#!/usr/bin/env python3
"""
build_index.py — Indexador Batch para la Base de Datos SQLite (Día 16).
Escanea los manifiestos en data/evidence/ y los archivos .sigmf-meta originales
para poblar data/index.sqlite.
"""

import json
from pathlib import Path
import sqlite3
import hashlib
import sys

# Agregar la raíz del proyecto al path para poder importar app.api.db
sys.path.append(str(Path(__file__).parent.parent))
from app.api.db import get_db_connection, init_db

EVIDENCE_DIR = Path("/workspace/data/evidence")
SAMPLES_DIR = Path("/workspace/rf-spectrum/data/samples")
INTERRUPTION_GAP_THRESHOLD_S = 5.0  # Gap > 5s entre eventos indica interrupción

def detect_interrupciones(eventos):
    """
    Detecta si hubo interrupciones analizando gaps temporales entre eventos.
    Una interrupción se infiere si hay gaps > INTERRUPTION_GAP_THRESHOLD_S
    entre eventos consecutivos (ordenados por start_t_s).
    """
    if len(eventos) <= 1:
        return False

    sorted_eventos = sorted(eventos, key=lambda e: e["event_metadata"]["start_t_s"])

    for i in range(len(sorted_eventos) - 1):
        end_actual = sorted_eventos[i]["event_metadata"]["end_t_s"]
        start_siguiente = sorted_eventos[i + 1]["event_metadata"]["start_t_s"]
        gap = start_siguiente - end_actual

        if gap > INTERRUPTION_GAP_THRESHOLD_S:
            return True

    return False

def compute_sha256(filepath):
    if not Path(filepath).exists():
        return None
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def find_meta_by_hash(target_hash: str) -> Path:
    """
    Busca el archivo original basándose en el hash y devuelve la ruta de su .sigmf-meta
    """
    for p in SAMPLES_DIR.rglob("*"):
        if p.is_file() and p.suffix in ['.iq', '.sigmf-data']:
            h = compute_sha256(p)
            if h and h.startswith(target_hash[:12]):
                # Reemplazar la extensión por .sigmf-meta
                meta_path = p.with_suffix('.sigmf-meta')
                if meta_path.exists():
                    return meta_path
    return None

def build_index():
    init_db()
    conn = get_db_connection()
    
    # Recolectar todos los manifiestos
    manifests = []
    if EVIDENCE_DIR.exists():
        for d in EVIDENCE_DIR.iterdir():
            if d.is_dir():
                mf = d / "manifest.json"
                if mf.exists():
                    with open(mf, 'r') as f:
                        try:
                            manifests.append(json.load(f))
                        except json.JSONDecodeError:
                            print(f"Error parseando {mf}")

    # Agrupar por sesión (capture_sha256)
    sessions = {}
    for m in manifests:
        em = m["event_metadata"]
        cap_hash = em["capture_sha256"]
        if cap_hash not in sessions:
            sessions[cap_hash] = {
                "session_id": em["session_id"],
                "capture_sha256": cap_hash,
                "events": []
            }
        sessions[cap_hash]["events"].append(m)

    print(f"[*] Encontradas {len(sessions)} sesiones y {len(manifests)} eventos en {EVIDENCE_DIR}")

    try:
        conn.execute("BEGIN TRANSACTION")
        
        # Primero limpiamos para reconstruir el índice de cero
        conn.execute("DELETE FROM events")
        conn.execute("DELETE FROM sessions")

        for cap_hash, s_data in sessions.items():
            session_id = s_data["session_id"]
            
            # Buscar metadata original
            meta_path = find_meta_by_hash(cap_hash)
            start_datetime = None
            fs_hz = None
            fc_hz = None
            duration_s = None
            ruta_meta = None
            
            if meta_path:
                ruta_meta = str(meta_path.relative_to(Path("/workspace")))
                with open(meta_path, 'r') as f:
                    orig_meta = json.load(f)
                    fs_hz = orig_meta.get("global", {}).get("core:sample_rate")
                    captures = orig_meta.get("captures", [])
                    if captures:
                        start_datetime = captures[0].get("core:datetime")
                        fc_hz = captures[0].get("core:frequency")
            else:
                print(f"⚠️ Metadata original no encontrada para la captura con hash {cap_hash[:12]}")
                
            n_events = len(s_data["events"])
            tuvo_interrupciones = detect_interrupciones(s_data["events"])

            # Insertar sesion
            conn.execute("""
                INSERT INTO sessions (session_id, capture_sha256, fc_hz, fs_hz, start_datetime, duration_s, n_events, ruta_meta, tuvo_interrupciones)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (session_id, cap_hash, fc_hz, fs_hz, start_datetime, duration_s, n_events, ruta_meta, tuvo_interrupciones))
            
            # Insertar eventos
            for m in s_data["events"]:
                em = m["event_metadata"]
                event_id = em["event_id"]
                # La ruta relativa para ruta_evidencia (directorio base de evidencia)
                # Ejemplo: data/evidence/19c10fbb7b7e_FM_Sub1_0001 pero relativo a DATA_ROOT
                # Nuestro DATA_ROOT es /workspace/data, por lo que relativo seria 'evidence/19c10fbb7b7e_FM_Sub1_0001'
                ruta_evidencia = f"evidence/{event_id}"
                
                conn.execute("""
                    INSERT INTO events (
                        event_id, session_id, band_name, rule_name, start_t_s, end_t_s, 
                        duration_s, pico_dbfs, potencia_media_activa_dbfs, severidad, 
                        confianza, closed_reason, ruta_evidencia
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    event_id, session_id, em["band_name"], em["rule_name"], 
                    em["start_t_s"], em["end_t_s"], em["duration_s"], 
                    em.get("pico_dbfs"), em.get("potencia_media_activa_dbfs"),
                    em.get("severidad"), em.get("confianza"), em.get("closed_reason"),
                    ruta_evidencia
                ))

        conn.commit()
        print(f"✅ Índice construido exitosamente en {get_db_connection().execute('PRAGMA database_list').fetchall()[0][2]}")
    except Exception as e:
        conn.rollback()
        print(f"❌ Error construyendo índice: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    build_index()
