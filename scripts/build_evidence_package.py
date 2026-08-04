#!/usr/bin/env python3
"""
build_evidence_package.py — CLI para generar paquetes de evidencia forense (Día 15).
"""

import argparse
import json
import sys
from pathlib import Path

# Agregar el root del proyecto al sys.path para importar app.evidence
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.evidence.builder import EvidenceBuilder

def main():
    parser = argparse.ArgumentParser(description="Empaquetador Forense de Evidencia")
    parser.add_argument("events", type=Path, help="Ruta al archivo eventos.json")
    parser.add_argument("--event-id", type=str, required=True, help="ID exacto del evento")
    parser.add_argument("--features", type=Path, required=True, help="Ruta al CSV con las features")
    parser.add_argument("--spectrogram", type=Path, required=True, help="Ruta al .npz original")
    parser.add_argument("--sigmf-data", type=Path, required=True, help="Ruta al archivo original .iq / .sigmf-data")
    parser.add_argument("--sigmf-meta", type=Path, required=True, help="Ruta al archivo original .sigmf-meta")
    parser.add_argument("--rules-config", type=Path, help="Ruta a rules_config.json")
    parser.add_argument("--features-config", type=Path, help="Ruta a features_config.json")
    parser.add_argument("--padding", type=float, default=0.5, help="Margen en segundos antes y despues del evento")
    parser.add_argument("--out-dir", type=Path, default=Path("data/evidence"), help="Directorio destino (default: data/evidence)")
    args = parser.parse_args()

    with open(args.events, 'r') as f:
        eventos = json.load(f)
    
    evento = next((e for e in eventos if e.get("event_id") == args.event_id), None)
    if not evento:
        print(f"Error: Evento {args.event_id} no encontrado en {args.events}")
        sys.exit(1)

    print(f"[*] Construyendo paquete de evidencia para: {args.event_id}")
    builder = EvidenceBuilder(out_dir=args.out_dir)
    
    pkg_dir = builder.build_package(
        evento=evento,
        features_csv_path=args.features,
        spectrogram_npz_path=args.spectrogram,
        sigmf_data_path=args.sigmf_data,
        sigmf_meta_path=args.sigmf_meta,
        rules_config_path=args.rules_config,
        features_config_path=args.features_config,
        padding_s=args.padding
    )
    print(f"\n✅ Evidencia empaquetada exitosamente en: {pkg_dir}/")

if __name__ == "__main__":
    main()
