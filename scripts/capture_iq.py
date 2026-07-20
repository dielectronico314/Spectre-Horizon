#!/usr/bin/env python3
"""
capture_iq.py
Script para capturar datos IQ (complejos) en formato binario desde el Harogic,
parametrizable mediante argumentos de línea de comandos.

Debe ejecutarse dentro de RF-Swift o mediante su wrapper.
"""

import argparse
import sys
import os

def parse_args():
    parser = argparse.ArgumentParser(description="Capturador de datos IQ para Harogic SDR (RF-Swift)")
    parser.add_argument("--freq", type=float, required=True,
                        help="Frecuencia central en Hz (ej. 106.5e6 para 106.5 MHz)")
    parser.add_argument("--rate", type=float, required=True,
                        help="Velocidad de muestreo en SPS (ej. 1.95e6)")
    parser.add_argument("--gain", type=float, default=0.0,
                        help="Ganancia en dB (por defecto 0.0)")
    parser.add_argument("--duration", type=float, default=10.0,
                        help="Duración de la captura en segundos (por defecto 10.0)")
    parser.add_argument("--outdir", type=str, default="/workspace/rf-spectrum/data/samples",
                        help="Directorio de salida para los archivos binarios")
    
    return parser.parse_args()

def main():
    # PASO 1: Recepción de Parámetros
    args = parse_args()
    
    print("==================================================")
    print(" 📡 INICIANDO CAPTURA IQ PARAMETRIZADA (Paso 1)   ")
    print("==================================================")
    print(f"Frecuencia Central : {args.freq / 1e6:.4f} MHz")
    print(f"Sample Rate        : {args.rate / 1e6:.4f} MSPS")
    print(f"Ganancia           : {args.gain} dB")
    print(f"Duración de Captura: {args.duration} segundos")
    print(f"Directorio Salida  : {args.outdir}")
    print("==================================================")
    
    # PASO 2: Inicialización y Configuración de Hardware
    print("🔌 [Paso 2] Conectando al Harogic SDR y aplicando configuración...")
    try:
        import SoapySDR
        # 1. Instanciamos el dispositivo
        sdr = SoapySDR.Device({"driver": "harogic"})
        direction = SoapySDR.SOAPY_SDR_RX
        canal = 0
        
        # 2. Asignamos los parámetros recibidos
        sdr.setSampleRate(direction, canal, args.rate)
        sdr.setFrequency(direction, canal, args.freq)
        sdr.setGain(direction, canal, args.gain)
        
        # Mostramos validación de la configuración
        real_rate = sdr.getSampleRate(direction, canal)
        print(f"✅ Hardware configurado exitosamente. Sample Rate real: {real_rate / 1e6:.4f} MSPS")
    except ImportError:
        print("❌ Error: No se pudo importar la librería SoapySDR.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error crítico al inicializar el hardware Harogic: {e}")
        sys.exit(1)
        
    # PASO 3: Activación del "Stream" (Canal de Datos)
    print("🌊 [Paso 3] Abriendo la tubería de datos bidireccional (Stream)...")
    try:
        # Configuramos el stream en formato CF32 (Complex Float 32-bit, nativo en Python)
        rxStream = sdr.setupStream(direction, SoapySDR.SOAPY_SDR_CF32)
        
        # Le preguntamos al Stream de qué tamaño serán los paquetes (MTU)
        mtu = sdr.getStreamMTU(rxStream)
        
        # Activamos el flujo de datos desde el hardware a la RAM
        sdr.activateStream(rxStream)
        print(f"✅ Stream activado exitosamente. Tamaño del paquete (MTU): {mtu} muestras.")
        
    except Exception as e:
        print(f"❌ Error al abrir el Stream de datos: {e}")
        sys.exit(1)
        
    # PASO 4: El Bucle de Captura y Escritura (Buffer)
    print(f"💾 [Paso 4] Iniciando captura de {args.duration} segundos...")
    import time
    from datetime import datetime
    import numpy as np
    
    # Asegurar que el directorio exista
    os.makedirs(args.outdir, exist_ok=True)
    
    # Crear subcarpeta de sesión
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_name = f"session_{timestamp}_{args.freq/1e6:.1f}MHz"
    session_dir = os.path.join(args.outdir, session_name)
    os.makedirs(session_dir, exist_ok=True)
    
    # Nombre de archivo dinámico dentro de la sesión
    filename = f"captura_{args.freq/1e6:.1f}MHz_{timestamp}.iq"
    filepath = os.path.join(session_dir, filename)
    
    # Si el MTU es 0 (falso negativo del binding), forzamos un bloque seguro
    buffer_size = mtu if mtu > 0 else 32768
    
    # Creamos nuestro "balde". Formato CF32 = np.complex64
    buff = np.zeros(buffer_size, np.complex64)

    samples_read = 0
    overflows_count = 0
    start_time = time.time()
    
    print(f"Escribiendo en crudo en: {filepath}")
    
    try:
        with open(filepath, 'wb') as f:
            while (time.time() - start_time) < args.duration:
                # El comando estrella: Leemos la tubería y lo metemos en el balde
                sr = sdr.readStream(rxStream, [buff], buffer_size, timeoutUs=1000000)
                
                if sr.ret > 0:
                    # Escribimos solo la porción del balde que se llenó en el disco
                    f.write(buff[:sr.ret].tobytes())
                    samples_read += sr.ret
                elif sr.ret == SoapySDR.SOAPY_SDR_TIMEOUT:
                    print("⚠️ Timeout: La antena se tardó en enviar datos.")
                elif sr.ret == SoapySDR.SOAPY_SDR_OVERFLOW:
                    print("⚠️ Overflow: La RAM no dio abasto, perdimos muestras de radio.")
                    overflows_count += 1
                elif sr.ret < 0:
                    print(f"❌ Error de lectura devuelto por el hardware: {sr.ret}")
                    break
    except KeyboardInterrupt:
        print("\n⏹️ Detenido por el usuario.")

    # Apagamos y cerramos la tubería de forma segura
    sdr.deactivateStream(rxStream)
    sdr.closeStream(rxStream)
    
    duration_real = time.time() - start_time
    megabytes = (samples_read * 8) / (1024 * 1024) # 8 bytes por complex64
    print("==================================================")
    print(f"✅ CAPTURA FINALIZADA")
    print(f"Muestras  : {samples_read:,}")
    print(f"Overflows : {overflows_count}")
    print(f"Tamaño IQ : {megabytes:.2f} MB")
    print(f"Tiempo real: {duration_real:.2f} segundos")
    print("==================================================")
    
    # PASO 5: Generación del Contrato Metadata (SigMF)
    print("📝 [Paso 5] Generando contrato de metadatos (SigMF)...")
    import json
    
    metadata = {
        "global": {
            "core:datatype": "cf32_le",
            "core:sample_rate": args.rate,
            "core:hw": "Harogic SDR",
            "core:author": "RF-Swift Automator",
            "core:version": "0.1.0"
        },
        "captures": [
            {
                "core:sample_start": 0,
                "core:frequency": args.freq,
                "core:datetime": datetime.utcnow().isoformat() + "Z",
                "core:overflows": overflows_count
            }
        ],
        "annotations": []
    }
    
    meta_filepath = filepath.replace('.iq', '.sigmf-meta')
    with open(meta_filepath, 'w') as f:
        json.dump(metadata, f, indent=4)
        
    print(f"✅ Metadata guardada exitosamente en: {meta_filepath}")

if __name__ == "__main__":
    main()
