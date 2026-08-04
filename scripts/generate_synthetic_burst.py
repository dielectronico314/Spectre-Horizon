#!/usr/bin/env python3
"""
generate_synthetic_burst.py
Genera una señal IQ sintética que contiene:
- Ruido blanco de fondo
- Un tono continuo (CW) para pruebas de piso de ruido espectral (Ej: banda de 50kHz)
- Un pulso intermitente (Burst) para pruebas de presencia temporal (Ej: banda de 200kHz)

Esto nos proveerá un 'ground truth' exacto para el Día 13 y Día 14.
"""

import os
import json
import hashlib
import numpy as np
from datetime import datetime, timezone

def main():
    sample_rate = 1953125.0
    center_freq = 106500000.0
    duration = 5.0
    num_samples = int(sample_rate * duration)
    
    output_dir = "/workspace/rf-spectrum/data/samples/test_burst_106p5MHz"
    os.makedirs(output_dir, exist_ok=True)
    
    iq_filepath = os.path.join(output_dir, "test_burst.iq")
    meta_filepath = os.path.join(output_dir, "test_burst.sigmf-meta")
    gt_filepath = os.path.join(output_dir, "ground_truth.json")
    
    fc_mhz = center_freq / 1e6
    print(f"📡 Generando Burst Sintético ({fc_mhz:.1f} MHz, {duration}s)...")
    
    t = np.arange(num_samples) / sample_rate
    
    # 1. Ruido Blanco (Piso de Ruido ~ constante)
    # Varianza = 0.01 -> std = 0.1
    # Potencia total teórica en todo el ancho de banda = 10 * log10(0.1^2 + 0.1^2) = 10 * log10(0.02) = -16.99 dBFS
    noise = (np.random.randn(num_samples) + 1j * np.random.randn(num_samples)) * 0.1
    
    # 2. Tono Continuo (CW) en 50 kHz
    # Amplitud = 0.2 -> Potencia teórica = 10 * log10(0.2^2) = -13.98 dBFS pico (aprox, dependiendo de la ventana)
    tone = 0.2 * np.exp(1j * 2 * np.pi * 50000.0 * t)
    
    # 3. Burst Intermitente en 200 kHz
    # Activo de t=1.0s a t=3.0s (duración exacta = 2.0s)
    # Amplitud = 0.5 -> Potencia teórica = 10 * log10(0.5^2) = -6.02 dBFS
    burst = 0.5 * np.exp(1j * 2 * np.pi * 200000.0 * t)
    
    # Aplicar ventana temporal al burst
    burst_mask = (t >= 1.0) & (t < 3.0)
    burst = burst * burst_mask
    
    # Señal final
    signal = (noise + tone + burst).astype(np.complex64)
    
    print(f"💾 Guardando archivo binario IQ: {iq_filepath}")
    signal.tofile(iq_filepath)
    
    print("🛡️ Calculando Hash SHA256...")
    sha256 = hashlib.sha256()
    with open(iq_filepath, 'rb') as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    dataset_hash = sha256.hexdigest()
    
    timestamp_iso = datetime.now(timezone.utc).isoformat(timespec='milliseconds') + 'Z'
    
    meta = {
        "global": {
            "core:datatype": "cf32_le",
            "core:sample_rate": sample_rate,
            "core:version": "1.0.0",
            "core:dataset_hash": dataset_hash,
            "core:recorder": "Spectre-Horizon Burst Generator"
        },
        "captures": [
            {
                "core:sample_start": 0,
                "core:frequency": center_freq,
                "core:datetime": timestamp_iso
            }
        ],
        "annotations": [],
        "input": {
            "center_freq_hz": center_freq,
            "data_sha256": dataset_hash
        }
    }
    
    with open(meta_filepath, 'w') as f:
        json.dump(meta, f, indent=4)
        
    # Guardar Ground Truth
    gt = {
        "cw_tone": {
            "freq_hz": 50000.0,
            "expected_peak_dbfs": 20 * np.log10(0.2)
        },
        "burst": {
            "freq_hz": 200000.0,
            "start_s": 1.0,
            "end_s": 3.0,
            "duration_s": 2.0,
            "expected_peak_dbfs": 20 * np.log10(0.5)
        }
    }
    
    with open(gt_filepath, 'w') as f:
        json.dump(gt, f, indent=4)
        
    print("✅ Burst sintético generado con éxito.")

if __name__ == "__main__":
    main()
