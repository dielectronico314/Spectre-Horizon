#!/usr/bin/env python3
"""
replay_iq.py
Script para reproducir (replay) capturas de RF de forma offline y determinista.
Día 9: Simulador de flujo en vivo con auditoría criptográfica.
"""

import argparse
import sys
import os
import time
import json
import hashlib
import logging
import numpy as np

# Configuración de logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("Spectre-Replay")

def verify_hash(filepath, expected_hash):
    """Calcula el SHA256 del archivo y lo compara con el esperado."""
    logger.info(f"🛡️ Calculando Hash SHA256 para auditoría: {os.path.basename(filepath)}")
    sha256 = hashlib.sha256()
    
    # Leer en bloques para no saturar RAM
    with open(filepath, 'rb') as f:
        while True:
            data = f.read(65536)
            if not data:
                break
            sha256.update(data)
            
    calculated_hash = sha256.hexdigest()
    if calculated_hash != expected_hash:
        logger.error(f"❌ [FAIL] Violación de Seguridad (Cadena de Custodia).")
        logger.error(f"Esperado: {expected_hash}")
        logger.error(f"Calculado: {calculated_hash}")
        sys.exit(1)
    else:
        logger.info(f"✅ [PASS] Hash verificado correctamente. Integridad intacta.")
        
def replay_stream(iq_path, sample_rate, chunk_samples=1000000):
    """
    Lee el archivo IQ en bloques y emula el tiempo real de transmisión.
    chunk_samples: Número de muestras a procesar en cada ciclo.
    """
    bytes_per_sample = 8 # cf32_le = 2 * 32-bit floats = 8 bytes
    chunk_bytes = chunk_samples * bytes_per_sample
    time_per_chunk = chunk_samples / sample_rate
    
    logger.info("==================================================")
    logger.info(" 📡 INICIANDO REPRODUCCIÓN (STREAM EMULATION) ")
    logger.info("==================================================")
    logger.info(f"Archivo     : {os.path.basename(iq_path)}")
    logger.info(f"Sample Rate : {sample_rate} SPS")
    logger.info(f"T. por bloque: {time_per_chunk:.3f} segundos")
    
    total_samples = 0
    start_time = time.time()
    
    try:
        with open(iq_path, 'rb') as f:
            while True:
                chunk_start = time.time()
                raw_data = f.read(chunk_bytes)
                if not raw_data:
                    break
                
                # Simular lectura en formato numpy
                data = np.frombuffer(raw_data, dtype=np.complex64)
                samples_read = len(data)
                total_samples += samples_read
                
                # === AQUÍ IRÍA LA LÓGICA DE PROCESAMIENTO (FFT, etc) ===
                # ...
                
                # Calcular el tiempo consumido en lectura/procesamiento
                elapsed = time.time() - chunk_start
                
                # Dormir el resto del tiempo para emular hardware en vivo
                sleep_time = (samples_read / sample_rate) - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)
                else:
                    logger.warning("⚠️ El procesamiento es más lento que el tiempo real (Underflow simulado)")
                
                # Feedback visual progresivo
                sys.stdout.write(".")
                sys.stdout.flush()
                
    except KeyboardInterrupt:
        logger.info("\n🛑 Reproducción cancelada por el usuario.")
    
    total_time = time.time() - start_time
    logger.info(f"\n✅ REPRODUCCIÓN FINALIZADA.")
    logger.info(f"Muestras leídas : {total_samples}")
    logger.info(f"Tiempo simulado : {total_samples / sample_rate:.2f} s")
    logger.info(f"Tiempo real     : {total_time:.2f} s")
    logger.info("==================================================")

def main():
    parser = argparse.ArgumentParser(description="Reproductor Offline Determinista para SigMF")
    parser.add_argument("--meta", type=str, required=True,
                        help="Ruta absoluta o relativa al archivo .sigmf-meta")
    args = parser.parse_args()

    meta_path = args.meta
    
    if not os.path.exists(meta_path):
        logger.error(f"No se encontró el archivo de metadatos: {meta_path}")
        sys.exit(1)
        
    # Asumimos que el .iq tiene el mismo nombre base
    base_path = os.path.splitext(meta_path)[0]
    iq_path = base_path + ".iq"
    
    if not os.path.exists(iq_path):
        logger.error(f"No se encontró el archivo IQ asociado: {iq_path}")
        sys.exit(1)

    logger.info(f"Leyendo metadatos SigMF: {os.path.basename(meta_path)}")
    with open(meta_path, 'r') as f:
        meta = json.load(f)
        
    try:
        sample_rate = meta["global"]["core:sample_rate"]
        expected_hash = meta["global"]["core:dataset_hash"]
    except KeyError as e:
        logger.error(f"Falta un campo requerido en el JSON para el Replay: {e}")
        sys.exit(1)
        
    # Auditoría
    verify_hash(iq_path, expected_hash)
    
    # Reproducción
    replay_stream(iq_path, sample_rate)

if __name__ == "__main__":
    main()
