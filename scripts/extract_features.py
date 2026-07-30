#!/usr/bin/env python3
import sys
import json
import argparse
from pathlib import Path
import numpy as np

# Añadir el raíz del proyecto al sys.path para importar features.py
sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.processing.features import (
    peak_marker, band_power_db, occupied_bandwidth,
    noise_floor_spectral, noise_floor_temporal, PresenceDetector
)

def main():
    parser = argparse.ArgumentParser(description="Extrae features paramétricas desde un espectrograma .npz")
    parser.add_argument("npz_file", type=Path)
    parser.add_argument("--config", type=Path, default="config/features_config.json")
    parser.add_argument("--out-dir", type=Path, default=".")
    
    args = parser.parse_args()
    
    if not args.npz_file.exists() or not args.config.exists():
        print("Error: Archivos no encontrados.")
        sys.exit(1)
        
    # Cargar Configuración
    with open(args.config, 'r') as f:
        config = json.load(f)
        
    # Cargar Espectrograma
    data = np.load(args.npz_file)
    dbfs = data["dbfs"]
    times = data["times_s"]
    freqs = data["freqs_hz"]
    
    session_id = args.npz_file.stem
    capture_sha256 = "NO_HASH"

    manifest_path = args.npz_file.with_name(args.npz_file.stem.replace("_espectrograma", "_manifest") + ".json")
    if manifest_path.exists():
        with open(manifest_path, 'r') as f:
            manifest = json.load(f)
            capture_sha256 = manifest.get("input", {}).get("data_sha256", "NO_HASH")
    
    # Pre-calcular ENBW_bins. Asumimos ventana de Hann (Día 11).
    enbw_bins = 1.5 
    
    out_csv = args.out_dir / f"features_{session_id}.csv"
    
    with open(out_csv, 'w') as f_csv:
        f_csv.write("session_id,capture_sha256,band_name,t_s,freq_pico_hz,pico_dbfs,potencia_dbfs,bw_hz,snr_db,presente\n")
        
        session_summary = []
        
        for band in config["bands"]:
            b_name = band["name"]
            f_low = band["freq_low_hz"]
            f_high = band["freq_high_hz"]
            
            # Índices de la banda
            idx_start = np.searchsorted(freqs, f_low)
            idx_end = np.searchsorted(freqs, f_high)
            
            if idx_start >= idx_end:
                continue
                
            freqs_band = freqs[idx_start:idx_end]
            
            # Arrays para estadísticas de sesión
            hist_pico = []
            hist_potencia = []
            hist_snr = []
            hist_bw = []
            
            # Si la estrategia es temporal, necesitamos hacer un pre-paso para calcular la potencia
            # de toda la sesión y estimar el piso en los silencios.
            nf_temporal = -300.0
            if band["noise_floor_strategy"] == "temporal":
                potencias = []
                for i in range(len(times)):
                    p = band_power_db(dbfs[i, idx_start:idx_end], enbw_bins)
                    potencias.append(p)
                potencias = np.array(potencias)
                # Tramas sin señal = tramas por debajo de la mediana
                mediana_global = np.median(potencias)
                tramas_silencio = potencias[potencias < mediana_global]
                nf_temporal = noise_floor_temporal(tramas_silencio)
            
            detector = PresenceDetector(
                margin_on_db=band["margin_on_db"],
                margin_off_db=band["margin_off_db"],
                required_consecutive=band.get("required_consecutive", 3)
            )
            
            frames_encendidos = 0
            
            # Pasada por trama
            for i in range(len(times)):
                frame = dbfs[i]
                band_frame = frame[idx_start:idx_end]
                t_s = times[i]
                
                pico_db, freq_pico = peak_marker(band_frame, freqs_band)
                pwr_db = band_power_db(band_frame, enbw_bins)
                bw = occupied_bandwidth(band_frame, freqs_band)
                
                if band["noise_floor_strategy"] == "spectral":
                    nf = noise_floor_spectral(frame, idx_start, idx_end)
                else:
                    nf = nf_temporal
                    
                snr = pwr_db - nf
                presente = detector.update(snr)
                
                if presente:
                    frames_encendidos += 1
                
                f_csv.write(f"{session_id},{capture_sha256},{b_name},{t_s:.6f},{freq_pico:.1f},{pico_db:.2f},{pwr_db:.2f},{bw:.1f},{snr:.2f},{presente}\n")
                
                hist_pico.append(pico_db)
                hist_potencia.append(pwr_db)
                hist_snr.append(snr)
                hist_bw.append(bw)
                
            # Agregar a resumen
            dt = times[1] - times[0] if len(times) > 1 else 0.0
            duracion_s = frames_encendidos * dt
            
            session_summary.append({
                "band_name": b_name,
                "duracion_activa_s": float(duracion_s),
                "pico_max_dbfs": float(np.max(hist_pico)),
                "potencia_media_dbfs": float(np.mean(hist_potencia)),
                "snr_media_db": float(np.mean(hist_snr)),
                "bw_media_hz": float(np.mean(hist_bw)),
                "n_tramas": len(times),
                "capture_sha256": capture_sha256
            })
            
    # Escribir JSON de resumen
    out_json = args.out_dir / f"resumen_{session_id}.json"
    with open(out_json, 'w') as f_json:
        json.dump(session_summary, f_json, indent=4)
        
    print(f"✅ Extracción completada.")
    print(f"   CSV: {out_csv}")
    print(f"   JSON: {out_json}")

if __name__ == "__main__":
    main()
