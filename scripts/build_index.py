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
import sys
try:
    from scripts.capture_iq import BACKOFF_RETRY_S
except ImportError:
    BACKOFF_RETRY_S = 5.0

def detect_interrupciones(session_dir: Path) -> bool:
    """
    Detecta si hubo interrupciones analizando gaps temporales entre los bloques
    reales guardados en disco (part00N.sigmf-meta).
    Un gap mayor a BACKOFF_RETRY_S indica que el hardware cayó y se reconectó.
    """
    if not session_dir or not session_dir.exists():
        return False

    meta_files = sorted(session_dir.glob("*.sigmf-meta"))
    if len(meta_files) <= 1:
        return False

    from datetime import datetime

    for i in range(len(meta_files) - 1):
        with open(meta_files[i], 'r') as f:
            meta1 = json.load(f)
        with open(meta_files[i+1], 'r') as f:
            meta2 = json.load(f)

        cap1 = meta1.get("captures", [{}])[0]
        cap2 = meta2.get("captures", [{}])[0]

        t1_iso = cap1.get("core:datetime")
        t2_iso = cap2.get("core:datetime")
        
        # Calcular dur1 desde el tamaño físico real, no el nominal
        dur1 = 0
        iq_file = meta_files[i].with_suffix('.iq')
        if not iq_file.exists():
            iq_file = meta_files[i].with_suffix('.sigmf-data')
            
        if iq_file.exists():
            fs = meta1.get("global", {}).get("core:sample_rate", 1.0)
            datatype = meta1.get("global", {}).get("core:datatype", "ci16_le")
            bytes_per_sample = 8 if datatype == "cf32_le" else 4
            dur1 = iq_file.stat().st_size / (bytes_per_sample * fs)
        else:
            dur1 = cap1.get("telemetry:duration_sec", 0)

        if not t1_iso or not t2_iso:
            continue

        t1 = datetime.fromisoformat(t1_iso.replace('Z', '+00:00'))
        t2 = datetime.fromisoformat(t2_iso.replace('Z', '+00:00'))

        gap_s = (t2 - t1).total_seconds() - dur1

        # Si el gap real es mayor que nuestro backoff (con un leve margen de latencia)
        if gap_s > (BACKOFF_RETRY_S * 0.9):
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

    # Agrupar por sesión (session_id)
    sessions = {}
    
    # 1. Escanear TODAS las sesiones base (tengan o no eventos)
    for meta_path in SAMPLES_DIR.rglob("*.sigmf-meta"):
        with open(meta_path, 'r') as f:
            try:
                orig_meta = json.load(f)
            except:
                continue
        
        cap_hash = orig_meta.get("global", {}).get("core:dataset_hash")
        if not cap_hash:
            # Fallback en caso de meta viejo sin dataset_hash
            iq_path = meta_path.with_suffix('.iq')
            if not iq_path.exists():
                iq_path = meta_path.with_suffix('.sigmf-data')
            if iq_path.exists():
                cap_hash = compute_sha256(iq_path)
        
        if not cap_hash:
            continue

        session_dir = meta_path.parent
        if session_dir.name.startswith("session_") or session_dir.name.startswith("test_"):
            session_id = session_dir.name
        else:
            session_id = f"{meta_path.stem}_espectrograma"

        fs_hz = orig_meta.get("global", {}).get("core:sample_rate")
        captures = orig_meta.get("captures", [])
        start_datetime = None
        fc_hz = None
        duration_s = None
        if captures:
            start_datetime = captures[0].get("core:datetime")
            fc_hz = captures[0].get("core:frequency")
            duration_s = captures[0].get("telemetry:duration_sec", 0)
        
        ruta_meta = str(meta_path.relative_to(Path("/workspace")))
        mtime = meta_path.stat().st_mtime
        
        # Guardar en el dict. Si hay multiples bloques, acumulamos duración y guardamos la meta del último bloque
        if session_id not in sessions:
            sessions[session_id] = {
                "session_id": session_id,
                "capture_sha256": cap_hash,
                "fc_hz": fc_hz,
                "fs_hz": fs_hz,
                "start_datetime": start_datetime,
                "duration_s": duration_s or 0,
                "ruta_meta": ruta_meta,
                "session_dir": session_dir,
                "events": [],
                "_mtime": mtime
            }
        else:
            # Acumular duracion
            sessions[session_id]["duration_s"] += (duration_s or 0)
            # Si este bloque es mas reciente, actualizar ruta_meta y hash
            if mtime > sessions[session_id]["_mtime"]:
                sessions[session_id]["capture_sha256"] = cap_hash
                sessions[session_id]["ruta_meta"] = ruta_meta
                sessions[session_id]["_mtime"] = mtime

    # 2. Agregar los eventos de evidence/ 
    for m in manifests:
        em = m["event_metadata"]
        session_id = em["session_id"]
        if session_id in sessions:
            sessions[session_id]["events"].append(m)
        else:
            # Evento huerfano (su captura no existe en samples/)
            sessions[session_id] = {
                "session_id": session_id,
                "capture_sha256": em["capture_sha256"],
                "fc_hz": None, "fs_hz": None, "start_datetime": None, "duration_s": None,
                "ruta_meta": None, "session_dir": None,
                "events": [m],
                "_mtime": 0
            }

    print(f"[*] Encontradas {len(sessions)} sesiones únicas y {len(manifests)} eventos")

    try:
        conn.execute("BEGIN TRANSACTION")
        
        conn.execute("DELETE FROM events")
        conn.execute("DELETE FROM sessions")

        for session_id, s_data in sessions.items():
            cap_hash = s_data["capture_sha256"]
            fc_hz = s_data["fc_hz"]
            fs_hz = s_data["fs_hz"]
            start_datetime = s_data["start_datetime"]
            duration_s = s_data["duration_s"]
            ruta_meta = s_data["ruta_meta"]
            
            if s_data["session_dir"]:
                tuvo_interrupciones = detect_interrupciones(s_data["session_dir"])
            else:
                tuvo_interrupciones = False
                
            n_events = len(s_data["events"])

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
