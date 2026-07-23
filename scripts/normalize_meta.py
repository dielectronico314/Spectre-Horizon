#!/usr/bin/env python3
"""
normalize_meta.py
Script para migrar archivos .sigmf-meta antiguos (v0.0) al nuevo Contrato (v0.1).
Inyecta los campos faltantes basándose en el tamaño del archivo IQ real.
"""

import os
import json

def get_file_size_mb(iq_filepath):
    if os.path.exists(iq_filepath):
        return round(os.path.getsize(iq_filepath) / (1024 * 1024), 2)
    return 0.0

def normalize_directory(directory):
    normalized_count = 0
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.sigmf-meta'):
                meta_path = os.path.join(root, file)
                iq_path = meta_path.replace('.sigmf-meta', '.iq')
                
                with open(meta_path, 'r') as f:
                    data = json.load(f)
                
                needs_update = False
                
                # Normalizar la sección global
                if "global" not in data:
                    data["global"] = {}
                if "core:version" not in data["global"]:
                    data["global"]["core:version"] = "0.2.0"
                    needs_update = True
                if "core:author" not in data["global"]:
                    data["global"]["core:author"] = "RF-Swift Automator (Day 7 Chunking)"
                    needs_update = True
                
                # Normalizar la captura
                if "captures" in data and len(data["captures"]) > 0:
                    cap = data["captures"][0]
                    
                    if "core:overflows" not in cap:
                        cap["core:overflows"] = 0
                        needs_update = True
                        
                    if "telemetry:duration_sec" not in cap:
                        cap["telemetry:duration_sec"] = 60.0 # Valor mock por defecto
                        needs_update = True
                        
                    if "telemetry:size_mb" not in cap:
                        cap["telemetry:size_mb"] = get_file_size_mb(iq_path)
                        needs_update = True
                        
                    if "telemetry:throughput_mbps" not in cap:
                        cap["telemetry:throughput_mbps"] = round(cap["telemetry:size_mb"] / 60.0, 2)
                        needs_update = True

                if needs_update:
                    with open(meta_path, 'w') as f:
                        json.dump(data, f, indent=4)
                    print(f"🔄 Archivo normalizado: {file}")
                    normalized_count += 1
    
    print(f"✅ Proceso completado. Archivos antiguos parcheados: {normalized_count}")

if __name__ == "__main__":
    target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "rf-spectrum", "data", "samples"))
    print(f"Normalizando directorio: {target_dir}")
    normalize_directory(target_dir)
