#!/usr/bin/env python3
"""
generate_synthetic_iq.py
Script para generar un archivo IQ sintético y su correspondiente metadato SigMF.
Útil para probar el sistema de Replay sin usar el Harogic real.
"""

import os
import json
import hashlib
import numpy as np
from datetime import datetime, timezone

def main():
    # Configuraciones de la señal sintética
    sample_rate = 2000000.0  # 2 MHz
    center_freq = 5000000000.0  # 5 GHz
    duration = 5.0  # 5 segundos de señal
    num_samples = int(sample_rate * duration)
    
    output_dir = "/workspace/rf-spectrum/data/samples/test_5GHz"
    os.makedirs(output_dir, exist_ok=True)
    
    iq_filename = "test_5GHz.iq"
    meta_filename = "test_5GHz.sigmf-meta"
    
    iq_filepath = os.path.join(output_dir, iq_filename)
    meta_filepath = os.path.join(output_dir, meta_filename)
    
    print(f"📡 Generando señal sintética (5 GHz, {duration}s)...")
    
    # 1. Generar Muestras Sintéticas (Ruido blanco + Tono)
    t = np.arange(num_samples) / sample_rate
    # Tono en 100 kHz (relativo a la freq central)
    tone = 0.5 * np.exp(1j * 2 * np.pi * 100000.0 * t) 
    noise = (np.random.randn(num_samples) + 1j * np.random.randn(num_samples)) * 0.1
    signal = (tone + noise).astype(np.complex64)
    
    # Escribir el binario
    print(f"💾 Guardando archivo binario IQ: {iq_filepath}")
    signal.tofile(iq_filepath)
    
    # 2. Calcular el SHA256
    print("🛡️ Calculando Hash SHA256...")
    sha256 = hashlib.sha256()
    with open(iq_filepath, 'rb') as f:
        while chunk := f.read(65536):
            sha256.update(chunk)
    dataset_hash = sha256.hexdigest()
    print(f"   Hash generado: {dataset_hash}")
    
    # 3. Generar el Contrato de Metadata SigMF v0.1
    timestamp_iso = datetime.now(timezone.utc).isoformat(timespec='milliseconds') + 'Z'
    
    meta = {
        "global": {
            "core:datatype": "cf32_le",
            "core:sample_rate": sample_rate,
            "core:version": "1.0.0",
            "core:dataset_hash": dataset_hash,
            "core:recorder": "Spectre-Horizon Synthetic Generator",
            "core:geolocation": "Simulado"
        },
        "captures": [
            {
                "core:sample_start": 0,
                "core:frequency": center_freq,
                "core:datetime": timestamp_iso,
                "core:antenna": "Virtual_Antenna",
                "core:gain": 0
            }
        ],
        "annotations": []
    }
    
    print(f"📝 Guardando archivo JSON SigMF: {meta_filepath}")
    with open(meta_filepath, 'w') as f:
        json.dump(meta, f, indent=4)
        
    print("\n✅ ¡Señal Sintética generada con éxito!")
    print("Para probar el Replay ejecuta:")
    print(f"./scripts/replay.sh rf-spectrum/data/samples/test_5GHz/{meta_filename}")

if __name__ == "__main__":
    main()
