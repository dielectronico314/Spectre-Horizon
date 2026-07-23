#!/usr/bin/env python3
"""
capture_iq.py
Script para capturar datos IQ (complejos) en formato binario desde el Harogic,
parametrizable mediante argumentos de línea de comandos.

Día 7: Tolerancia a fallos, partición por bloques (Chunking) y Reconexión (Backoff Retry)
"""

import argparse
import sys
import os
import time
from datetime import datetime, timezone
import numpy as np
import logging
import threading
import psutil
import json
import hashlib

# Forzar zona horaria a Caracas para los logs locales dentro del contenedor
os.environ['TZ'] = 'America/Caracas'
try:
    time.tzset()
except AttributeError:
    pass # tzset no está disponible en Windows, pero estamos en Linux

# ==========================================
# CONFIGURACIÓN DE OBSERVABILIDAD
# ==========================================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("Spectre-Horizon")

stop_telemetry = threading.Event()

def telemetry_worker(interval=30.0, session_dir=""):
    """Hilo en background para loguear uso de CPU, RAM y Disco."""
    logger.info("📡 Iniciando subsistema de telemetría de hardware...")
    disk_path = session_dir if session_dir else "/"
    
    while not stop_telemetry.is_set():
        cpu_usage = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory()
        
        try:
            disk = psutil.disk_usage(disk_path)
            disk_free_gb = disk.free / (1024**3)
            disk_str = f"{disk_free_gb:.1f} GB libres"
        except:
            disk_str = "N/A"
            
        logger.info(f"📊 [TELEMETRÍA] CPU: {cpu_usage:05.1f}% | RAM Uso: {mem.percent:05.1f}% | Disco: {disk_str}")
        stop_telemetry.wait(interval)
        
    logger.info("📡 Subsistema de telemetría detenido.")

# ==========================================
# CLI Y LÓGICA PRINCIPAL
# ==========================================
def parse_args():
    parser = argparse.ArgumentParser(description="Capturador de datos IQ para Harogic SDR con Telemetría y Chunking")
    parser.add_argument("--freq", type=float, required=True,
                        help="Frecuencia central en Hz (ej. 106.5e6)")
    parser.add_argument("--rate", type=float, required=True,
                        help="Velocidad de muestreo en SPS (ej. 1.95e6)")
    parser.add_argument("--gain", type=float, default=0.0,
                        help="Ganancia en dB")
    parser.add_argument("--duration", type=float, default=60.0,
                        help="Duración TOTAL de la sesión en segundos")
    parser.add_argument("--chunk-duration", type=float, default=60.0,
                        help="Duración de cada archivo individual en segundos (por defecto 60s)")
    parser.add_argument("--outdir", type=str, default="/workspace/rf-spectrum/data/samples",
                        help="Directorio de salida")
    parser.add_argument("--antenna", type=str, default="Dipolo_Bigotes",
                        help="Nombre/Tipo de antena conectada")
    parser.add_argument("--location", type=str, default="Laboratorio Local",
                        help="Ubicación o coordenadas de la sesión")
    
    return parser.parse_args()

def save_sigmf_meta(filepath, args, samples_read, overflows_count, duration_real):
    """Guarda los metadatos de un bloque (chunk) específico."""
    megabytes = (samples_read * 8) / (1024 * 1024)
    throughput_mbps = megabytes / duration_real if duration_real > 0 else 0
    
    # Calcular el Hash SHA256 del binario IQ (Para core:dataset_hash)
    file_hash = ""
    if os.path.exists(filepath):
        sha256 = hashlib.sha256()
        with open(filepath, 'rb') as f_iq:
            while True:
                data = f_iq.read(65536)
                if not data:
                    break
                sha256.update(data)
        file_hash = sha256.hexdigest()
    
    metadata = {
        "global": {
            "core:datatype": "cf32_le",
            "core:sample_rate": args.rate,
            "core:hw": "Harogic SAN-400 (CalFile: Interno)",
            "core:author": "RF-Swift Automator",
            "core:version": "0.2.1",
            "core:recorder": "Spectre-Horizon Core v0.2.1",
            "core:geolocation": args.location,
            "core:dataset_hash": file_hash
        },
        "captures": [
            {
                "core:sample_start": 0,
                "core:frequency": args.freq,
                "core:datetime": datetime.now(timezone.utc).isoformat(),
                "core:overflows": overflows_count,
                "core:antenna": args.antenna,
                "core:gain": args.gain,
                "telemetry:duration_sec": round(duration_real, 2),
                "telemetry:throughput_mbps": round(throughput_mbps, 2),
                "telemetry:size_mb": round(megabytes, 2)
            }
        ],
        "annotations": []
    }
    
    meta_filepath = filepath.replace('.iq', '.sigmf-meta')
    with open(meta_filepath, 'w') as f:
        json.dump(metadata, f, indent=4)
    logger.info(f"✅ Metadata guardada exitosamente: {os.path.basename(meta_filepath)}")

def main():
    args = parse_args()
    
    logger.info("==================================================")
    logger.info(" 📡 INICIANDO SESIÓN RESILIENTE (Día 7)           ")
    logger.info("==================================================")
    logger.info(f"Frecuencia         : {args.freq / 1e6:.4f} MHz")
    logger.info(f"Duración Total     : {args.duration} segundos")
    logger.info(f"Tamaño de Bloque   : {args.chunk_duration} segundos")
    logger.info("==================================================")
    
    # Crear carpeta de sesión una sola vez
    os.makedirs(args.outdir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_name = f"session_{timestamp}_{args.freq/1e6:.1f}MHz"
    session_dir = os.path.join(args.outdir, session_name)
    os.makedirs(session_dir, exist_ok=True)
    
    # Iniciar telemetría
    psutil.cpu_percent(interval=0.1)
    telemetry_thread = threading.Thread(target=telemetry_worker, args=(30.0, session_dir))
    telemetry_thread.daemon = True
    telemetry_thread.start()

    global_start_time = time.time()
    chunk_index = 1
    
    # ==============================================================
    # BUCLE GLOBAL (Sobrevive a desconexiones)
    # ==============================================================
    while (time.time() - global_start_time) < args.duration:
        try:
            import SoapySDR
            logger.info("🔌 Intentando conectar al hardware Harogic...")
            sdr = SoapySDR.Device({"driver": "harogic"})
            direction = SoapySDR.SOAPY_SDR_RX
            canal = 0
            
            sdr.setSampleRate(direction, canal, args.rate)
            sdr.setFrequency(direction, canal, args.freq)
            sdr.setGain(direction, canal, args.gain)
            
            rxStream = sdr.setupStream(direction, SoapySDR.SOAPY_SDR_CF32)
            mtu = sdr.getStreamMTU(rxStream)
            sdr.activateStream(rxStream)
            buffer_size = mtu if mtu > 0 else 32768
            buff = np.zeros(buffer_size, np.complex64)
            logger.info("✅ SDR Inicializado y Stream activado correctamente.")
            
            # ==============================================================
            # BUCLE DE CHUNKING (Corta archivos cada X segundos)
            # ==============================================================
            while (time.time() - global_start_time) < args.duration:
                chunk_start_time = time.time()
                filename = f"captura_{args.freq/1e6:.1f}MHz_part{chunk_index:03d}.iq"
                filepath = os.path.join(session_dir, filename)
                
                logger.info(f"💾 Iniciando grabación de bloque: {filename}")
                samples_read = 0
                overflows_count = 0
                
                with open(filepath, 'wb') as f:
                    while (time.time() - chunk_start_time) < args.chunk_duration:
                        # Revisar si se acabó el tiempo global
                        if (time.time() - global_start_time) >= args.duration:
                            break
                            
                        sr = sdr.readStream(rxStream, [buff], buffer_size, timeoutUs=1000000)
                        
                        if sr.ret > 0:
                            f.write(buff[:sr.ret].tobytes())
                            samples_read += sr.ret
                        elif sr.ret == SoapySDR.SOAPY_SDR_TIMEOUT:
                            logger.warning("⚠️ Timeout: Posible desconexión o retardo.")
                        elif sr.ret == SoapySDR.SOAPY_SDR_OVERFLOW:
                            overflows_count += 1
                        elif sr.ret < 0:
                            raise Exception(f"Error crítico en readStream (hardware desconectado): {sr.ret}")
                
                # Al cerrar el archivo (terminó el bloque o falló), guardamos su metadata
                duration_real = time.time() - chunk_start_time
                if samples_read > 0:
                    save_sigmf_meta(filepath, args, samples_read, overflows_count, duration_real)
                else:
                    logger.warning(f"🗑️ Bloque {filename} vacío, ignorando metadatos.")
                    
                chunk_index += 1
                
        except KeyboardInterrupt:
            logger.warning("⏹️ Detenido manualmente por el usuario.")
            break
        except Exception as e:
            logger.error(f"❌ FALLO DE HARDWARE DETECTADO: {e}")
            logger.warning("⏳ Esperando 5 segundos antes de reintentar la conexión (Backoff)...")
            time.sleep(5)
            # El ciclo global 'while' volverá al inicio y reintentará instanciar SoapySDR
        finally:
            try:
                # Intento de cierre seguro de la conexión anterior si existe
                sdr.deactivateStream(rxStream)
                sdr.closeStream(rxStream)
            except:
                pass

    # ==========================================
    # CIERRE DE SESIÓN
    # ==========================================
    stop_telemetry.set()
    telemetry_thread.join()
    
    total_time = time.time() - global_start_time
    logger.info("==================================================")
    logger.info(f"✅ SESIÓN FINALIZADA (Tiempo total: {total_time:.1f}s)")
    logger.info(f"Bloques extraídos: {chunk_index - 1}")
    logger.info("==================================================")

if __name__ == "__main__":
    main()
