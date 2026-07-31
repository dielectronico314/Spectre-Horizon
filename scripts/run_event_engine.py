#!/usr/bin/env python3
"""
run_event_engine.py — CLI del motor de eventos (Día 14).

Entrada: features_<sesion>.csv (salida de scripts/extract_features.py, Día 13).
Salida: eventos_<sesion>.json — lista de eventos con ciclo de vida completo.

No recalcula piso de ruido ni potencia: reutiliza snr_db, pico_dbfs y
potencia_dbfs ya calculados por banda/trama en Día 13. Ver docs/EVENTS_REF.md.
"""
import sys
import csv
import json
import argparse
from pathlib import Path
from collections import defaultdict

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.events.engine import EventEngine


def band_params(rules_config: dict, band_name: str) -> dict:
    """
    Orden de resolucion: defaults -> profiles[profile] -> bands[band_name]
    (sin la clave 'profile', que solo indica cual perfil usar).
    Ver config/rules_config.json y docs/EVENTS_REF.md.
    """
    defaults = rules_config.get("defaults", {})
    band_cfg = dict(rules_config.get("bands", {}).get(band_name, {}))
    profile_name = band_cfg.pop("profile", None)
    profile_cfg = rules_config.get("profiles", {}).get(profile_name, {}) if profile_name else {}
    return {**defaults, **profile_cfg, **band_cfg}


def main():
    parser = argparse.ArgumentParser(description="Motor de eventos por reglas: procesa features_<sesion>.csv y genera eventos_<sesion>.json")
    parser.add_argument("features_csv", type=Path)
    parser.add_argument("--rules-config", type=Path, default=Path("config/rules_config.json"))
    parser.add_argument("--out-dir", type=Path, default=Path("."))
    args = parser.parse_args()

    if not args.features_csv.exists() or not args.rules_config.exists():
        print("Error: Archivos no encontrados.")
        sys.exit(1)

    with open(args.rules_config, 'r') as f:
        rules_config = json.load(f)

    rows_by_band = defaultdict(list)
    with open(args.features_csv, newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows_by_band[row["band_name"]].append(row)

    if not rows_by_band:
        print("Error: El CSV no contiene tramas.")
        sys.exit(1)

    # session_id/sha256 son los mismos para todas las filas del CSV (una sesion)
    any_row = next(iter(rows_by_band.values()))[0]
    session_id = any_row["session_id"]
    capture_sha256 = any_row["capture_sha256"]

    all_events = []
    for band_name, rows in rows_by_band.items():
        params = band_params(rules_config, band_name)
        engine = EventEngine(
            band_name=band_name,
            margen_umbral_db=float(params["margen_umbral_db"]),
            min_on_frames=int(params.get("min_on_frames", 3)),
            min_off_frames=int(params.get("min_off_frames", 3)),
            merge_gap_s=float(params.get("merge_gap_s", 0.5)),
            margen_severidad_medium_db=float(params.get("margen_severidad_medium_db", 6.0)),
            margen_severidad_high_db=float(params.get("margen_severidad_high_db", 12.0)),
            confianza_escala_db=float(params.get("confianza_escala_db", 10.0)),
            session_id=session_id,
            capture_sha256=capture_sha256,
        )

        for row in rows:
            closed = engine.process_frame(
                t_s=float(row["t_s"]),
                snr_db=float(row["snr_db"]),
                pico_dbfs=float(row["pico_dbfs"]),
                potencia_dbfs=float(row["potencia_dbfs"]),
            )
            if closed is not None:
                all_events.append(closed)

        closed = engine.flush()
        if closed is not None:
            all_events.append(closed)

    all_events.sort(key=lambda e: e["start_t_s"])

    out_json = args.out_dir / f"eventos_{session_id}.json"
    args.out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_json, 'w') as f:
        json.dump(all_events, f, indent=4)

    print(f"✅ Motor de eventos completado.")
    print(f"   Eventos detectados: {len(all_events)}")
    print(f"   JSON: {out_json}")


if __name__ == "__main__":
    main()
