#!/usr/bin/env python3
import sys
import json
import subprocess
from pathlib import Path

def main():
    if len(sys.argv) < 3:
        print("Uso: batch_evidence_builder.py <eventos.json> <session_dir>")
        sys.exit(1)
        
    eventos_json = Path(sys.argv[1])
    session_dir = Path(sys.argv[2])
    
    if not eventos_json.exists():
        print(f"Error: No existe {eventos_json}")
        sys.exit(1)
        
    with open(eventos_json, 'r') as f:
        eventos = json.load(f)
        
    if not eventos:
        print("No hay eventos en el JSON. Saltando empaquetado.")
        sys.exit(0)
        
    print(f"[*] Encontrados {len(eventos)} eventos. Empaquetando...")
    
    for ev in eventos:
        event_id = ev["event_id"]
        # Buscar los archivos correspondientes a esta sesion
        npz = list(session_dir.glob("*_espectrograma.npz"))[0]
        csv = list(session_dir.glob("features_*.csv"))[0]
        meta = list(session_dir.glob("*.sigmf-meta"))[0]
        iq = list(session_dir.glob("*.iq"))[0]
        
        cmd = [
            "python3", "scripts/build_evidence_package.py", str(eventos_json),
            "--event-id", event_id,
            "--features", str(csv),
            "--spectrogram", str(npz),
            "--sigmf-data", str(iq),
            "--sigmf-meta", str(meta)
        ]
        print(f" -> Empaquetando {event_id}...")
        subprocess.run(cmd, check=True)
        
    print("✅ Todos los eventos empaquetados.")

if __name__ == "__main__":
    main()
