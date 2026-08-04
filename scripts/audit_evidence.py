#!/usr/bin/env python3
"""
audit_evidence.py — Auditor Forense de Evidencia (Día 15, Fase 2).

Verifica la integridad de un paquete de evidencia generado por build_evidence_package.py
en tres niveles de profundidad:
1. Hash local: Verifica hashes SHA-256 internos contra el manifiesto.
2. Trazabilidad: Busca el hash de la captura original en disco.
3. Reproducibilidad Matemática: Recalcula FFT y métricas DSP desde el IQ recortado.
"""

import argparse
import json
import hashlib
from pathlib import Path
import subprocess
import tempfile
import pandas as pd
import sys

def compute_sha256(filepath):
    if not Path(filepath).exists():
        return None
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

def find_capture_by_hash(samples_dir: Path, target_hash: str):
    """Busca un archivo .iq o .sigmf-data cuyo hash empiece con target_hash."""
    for p in samples_dir.rglob("*"):
        if p.is_file() and p.suffix in ['.iq', '.sigmf-data']:
            h = compute_sha256(p)
            if h and h.startswith(target_hash):
                return p
    return None

def audit_event(event_id: str, nivel: int, evidence_dir: Path, samples_dir: Path) -> dict:
    pkg_dir = evidence_dir / event_id
    if not pkg_dir.exists():
        return {"status": "ERROR", "msg": f"Directorio no encontrado: {pkg_dir}"}
    
    manifest_path = pkg_dir / "manifest.json"
    if not manifest_path.exists():
        return {"status": "ERROR", "msg": f"Manifiesto no encontrado en {pkg_dir}"}
    
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)

    # ---------------------------------------------------------
    # NIVEL 1: Existencia + Hash
    # ---------------------------------------------------------
    for fname, expected_hash in manifest["files_sha256"].items():
        fpath = pkg_dir / fname
        if not fpath.exists():
            return {"status": "FAIL", "nivel": 1, "msg": f"Falta archivo: {fname}"}
        actual_hash = compute_sha256(fpath)
        if actual_hash != expected_hash:
            return {"status": "FAIL", "nivel": 1, "msg": f"Hash mismatch en {fname}"}
    
    # Validar hash del propio manifiesto
    expected_manifest_hash = manifest.get("manifest_sha256")
    manifest_string = json.dumps({k:v for k,v in manifest.items() if k != "manifest_sha256"}, sort_keys=True)
    actual_manifest_hash = hashlib.sha256(manifest_string.encode()).hexdigest()
    if actual_manifest_hash != expected_manifest_hash:
        return {"status": "FAIL", "nivel": 1, "msg": "El manifiesto fue alterado (hash mismatch interno)"}
    
    if nivel == 1:
        return {"status": "PASS", "nivel": 1, "msg": "Hashes locales OK"}

    # ---------------------------------------------------------
    # NIVEL 2: Trazabilidad
    # ---------------------------------------------------------
    target_hash = manifest["event_metadata"]["capture_sha256"]
    # We will search by matching prefix (12 chars usually) to save time, but full compute is done
    orig_file = find_capture_by_hash(samples_dir, target_hash[:12])
    if not orig_file:
        return {"status": "FAIL", "nivel": 2, "msg": f"Captura original con hash {target_hash[:12]} no encontrada"}
    
    # For forensic safety, compute full hash
    full_hash = compute_sha256(orig_file)
    if full_hash != target_hash:
        return {"status": "FAIL", "nivel": 2, "msg": f"Captura original encontrada pero hash difiere. Original: {full_hash}"}

    if nivel == 2:
        return {"status": "PASS", "nivel": 2, "msg": f"Trazabilidad OK ({orig_file.name})"}

    # ---------------------------------------------------------
    # NIVEL 3: Reproducibilidad Matemática
    # ---------------------------------------------------------
    with tempfile.TemporaryDirectory() as tmpdirname:
        tmpdir = Path(tmpdirname)
        
        # 1. Volcar configs a archivos temporales
        spec_cfg = tmpdir / "spec_cfg.json"
        with open(spec_cfg, 'w') as f:
            json.dump(manifest.get("config_resuelto", {}).get("fft", {}), f)
            
        feat_cfg = tmpdir / "feat_cfg.json"
        with open(feat_cfg, 'w') as f:
            json.dump(manifest.get("config_resuelto", {}).get("features", {}), f)
            
        # 2. Correr Espectrograma
        sigmf_meta = pkg_dir / "evento.sigmf-meta"
        cmd_spec = [
            "python3", "/workspace/scripts/generate_spectrogram.py",
            str(sigmf_meta),
            "--config", str(spec_cfg),
            "--outdir", str(tmpdir)
        ]
        res = subprocess.run(cmd_spec, capture_output=True, text=True)
        if res.returncode != 0:
            return {"status": "FAIL", "nivel": 3, "msg": f"Error en generacion de espectrograma: {res.stderr}"}
            
        # 3. Correr Extractor de Features
        # The generate_spectrogram.py outputs a .npz with the same prefix as the meta file in the outdir
        # Assuming the name is 'evento_espectrograma.npz' or 'evento.npz'
        # Let's find the .npz in tmpdir
        npz_files = list(tmpdir.glob("*.npz"))
        if not npz_files:
            return {"status": "FAIL", "nivel": 3, "msg": "generate_spectrogram no produjo archivo .npz"}
        npz_file = npz_files[0]
        
        cmd_feat = [
            "python3", "/workspace/scripts/extract_features.py",
            str(npz_file),
            "--config", str(feat_cfg),
            "--spec-config", str(spec_cfg),
            "--out-dir", str(tmpdir)
        ]
        res = subprocess.run(cmd_feat, capture_output=True, text=True)
        if res.returncode != 0:
            return {"status": "FAIL", "nivel": 3, "msg": f"Error en generacion de features: {res.stderr}"}
            
        # 4. Leer CSV generado y comparar matemáticas
        csv_files = list(tmpdir.glob("*.csv"))
        if not csv_files:
            return {"status": "FAIL", "nivel": 3, "msg": "extract_features no produjo archivo .csv"}
        csv_file = csv_files[0]
        
        df = pd.read_csv(csv_file)
        
        # Filtro de banda si la config tiene multiples, pero aqui usamos la banda del evento
        band_name = manifest["event_metadata"]["band_name"]
        df_band = df[df['band_name'] == band_name]
        if df_band.empty:
            return {"status": "FAIL", "nivel": 3, "msg": f"No se genero features para la banda {band_name}"}
        
        # The original event metrics were calculated using logic in run_event_engine over specific active frames.
        # But for reproducibility, we can check the absolute peak in the re-generated slice.
        recalc_pico = df_band['pico_dbfs'].max()
        
        orig_pico = manifest["event_metadata"]["pico_dbfs"]
        delta_pico = abs(recalc_pico - orig_pico)
        
        # For average power it's trickier because it depends on the exact frames that were "ON".
        # We will strictly check the peak power to prove mathematical fidelity of the FFT stack.
        if delta_pico > 0.1:
            return {"status": "FAIL", "nivel": 3, "msg": f"Desviacion matematica! Pico original: {orig_pico}, Recalculado: {recalc_pico} (Delta: {delta_pico})"}

        return {"status": "PASS", "nivel": 3, "msg": f"Reproducibilidad OK (Delta Pico: {delta_pico:.3f} dB)"}


def main():
    parser = argparse.ArgumentParser(description="Auditor Forense de Evidencia")
    parser.add_argument("--event-id", type=str, help="ID del evento a auditar. Si no se provee, audita todos.")
    parser.add_argument("--nivel", type=int, choices=[1, 2, 3], default=3, help="Nivel de profundidad (1=Hashes, 2=Traza, 3=Matematico)")
    parser.add_argument("--evidence-dir", type=Path, default=Path("/workspace/data/evidence"), help="Directorio de paquetes de evidencia")
    parser.add_argument("--samples-dir", type=Path, default=Path("/workspace/rf-spectrum/data/samples"), help="Directorio de capturas originales")
    args = parser.parse_args()

    # Create directories if not exist to avoid crashing when iterating
    args.evidence_dir.mkdir(parents=True, exist_ok=True)
    args.samples_dir.mkdir(parents=True, exist_ok=True)

    if args.event_id:
        events = [args.event_id]
    else:
        events = [p.name for p in args.evidence_dir.iterdir() if p.is_dir()]
        
    if not events:
        print("No se encontraron eventos para auditar.")
        sys.exit(0)

    print(f"[*] Iniciando auditoría Nivel {args.nivel} sobre {len(events)} eventos...")
    print("-" * 60)
    
    all_pass = True
    for eid in sorted(events):
        res = audit_event(eid, args.nivel, args.evidence_dir, args.samples_dir)
        status = res["status"]
        if status == "PASS":
            print(f"✅ {eid:<35} | {status} | {res['msg']}")
        else:
            print(f"❌ {eid:<35} | {status} | {res['msg']}")
            all_pass = False

    print("-" * 60)
    if all_pass:
        print("🎉 AUDITORIA COMPLETADA: TODOS LOS EVENTOS APROBADOS.")
        sys.exit(0)
    else:
        print("⚠️ AUDITORIA FALLIDA: SE ENCONTRARON ANOMALIAS.")
        sys.exit(1)

if __name__ == "__main__":
    main()
