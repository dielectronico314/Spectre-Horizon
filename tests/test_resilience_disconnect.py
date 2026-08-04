#!/usr/bin/env python3
import sys
import os
import time
import json
from unittest.mock import MagicMock
import shutil

import numpy as np

# Inyectar mock de SoapySDR
class MockDevice:
    def __init__(self, *args, **kwargs):
        self.start_time = time.time()
        self.read_count = 0
        self.sample_index = 0
        self.fs = 1.95e6
        self.f_tone = 50e3 # Tono a 50 kHz offset
        
    def setSampleRate(self, *args): pass
    def setFrequency(self, *args): pass
    def setGain(self, *args): pass
    def setupStream(self, *args): return "mock_stream"
    def getStreamMTU(self, *args): return 32768
    def activateStream(self, *args): pass
    def deactivateStream(self, *args): pass
    def closeStream(self, *args): pass
    
    def readStream(self, stream, buffs, length, timeoutUs=1000000):
        time.sleep(0.1)  # Simular tiempo de hardware
        self.read_count += 1
        elapsed = time.time() - self.start_time
        
        # Simularemos un error de hardware (-2) a los 1.5 segundos
        if elapsed > 1.5:
            ret = MagicMock()
            ret.ret = -2 # Simula error por desconexión
            return ret
        else:
            ret = MagicMock()
            n_samps = min(length, int(self.fs * 0.1))
            ret.ret = n_samps
            
            # Generar tono continuo en memoria
            t = (self.sample_index + np.arange(n_samps)) / self.fs
            cw = 0.5 * np.exp(2j * np.pi * self.f_tone * t).astype(np.complex64)
            buffs[0][:n_samps] = cw
            self.sample_index += n_samps
            
            return ret

class MockSoapySDR:
    SOAPY_SDR_RX = 0
    SOAPY_SDR_CS16 = "CS16"
    SOAPY_SDR_TIMEOUT = -1
    SOAPY_SDR_OVERFLOW = -4
    Device = MockDevice

sys.modules['SoapySDR'] = MockSoapySDR()

# Reducir el backoff de 5s a 0.1s para que el test sea rápido
sys.path.append('scripts')
import capture_iq
_original_sleep = time.sleep
capture_iq.time.sleep = lambda x: _original_sleep(0.1)

# Forzar argumentos
outdir = 'tests/test_out'
if os.path.exists(outdir):
    shutil.rmtree(outdir)
    
sys.argv = [
    'capture_iq.py', 
    '--freq', '923e6', 
    '--rate', '1.95e6', 
    '--duration', '5',         # Total 5s
    '--chunk-duration', '10',  # Un chunk duraría 10s teóricamente
    '--outdir', outdir
]

print("Iniciando Test Automatizado de Resiliencia a Desconexión...")
capture_iq.main()

# Validar resultados
session_dirs = os.listdir(outdir)
if not session_dirs:
    print("❌ Test Fallido: No se creó el directorio de sesión.")
    sys.exit(1)

session_path = os.path.join(outdir, session_dirs[0])
iq_files = sorted([f for f in os.listdir(session_path) if f.endswith('.iq')])
meta_files = sorted([f for f in os.listdir(session_path) if f.endswith('.sigmf-meta')])

print(f"\nResultados del Test:")
print(f"Archivos IQ generados: {iq_files}")
print(f"Archivos Meta generados: {meta_files}")

if len(iq_files) >= 3 and len(meta_files) >= 3:
    print("✅ TEST FASE 1 PASADO: Múltiples archivos creados.")
else:
    print("❌ TEST FALLIDO: No se generaron suficientes archivos independientes.")
    sys.exit(1)

print("\n[*] FASE 2: Verificando la continuidad de la señal (DSP)...")
import subprocess
import glob

# Usar el procesador de docker para extraer features y validar el tono CW
# Crearemos un config temporal
test_config = os.path.join(outdir, "test_config.json")
with open(test_config, "w") as f:
    json.dump({
        "bands": [{
            "name": "CW_Mock",
            "offset_hz_low": 48000,
            "offset_hz_high": 52000,
            "noise_floor_strategy": "spectral",
            "margin_on_db": 10.0,
            "margin_off_db": 5.0
        }]
    }, f)

# Ejecutar DSP en cada archivo
for meta in meta_files:
    meta_path = os.path.join(session_path, meta)
    
    # Espectrograma
    cmd1 = ["docker", "exec", "-w", "/workspace", "harogic_final", "python3", "scripts/generate_spectrogram.py", meta_path, "-o", session_path]
    subprocess.run(cmd1, check=True, stdout=subprocess.DEVNULL)
    
    # Extraer features (la ruta del NPZ y CSV)
    npz_path = meta_path.replace(".sigmf-meta", "_espectrograma.npz")
    cmd2 = ["docker", "exec", "-w", "/workspace", "harogic_final", "python3", "scripts/extract_features.py", npz_path, "--config", test_config, "--out-dir", session_path]
    subprocess.run(cmd2, check=True, stdout=subprocess.DEVNULL)
    
    # Validar JSON de features
    json_res = npz_path.replace("captura", "resumen_captura").replace(".npz", ".json")
    with open(json_res, "r") as f:
        resumen = json.load(f)[0]
    
    # El archivo tiene datos?
    duracion = resumen["duracion_activa_s"]
    pico = resumen["pico_max_dbfs"]
    print(f" -> {meta}: Duración Activa CW = {duracion:.2f}s | SNR = {resumen['snr_media_db']:.1f} dB")
    
    if duracion <= 0.0 or resumen["snr_media_db"] < 20.0:
        print("❌ TEST FALLIDO: La señal CW no fue detectada correctamente o se perdió.")
        sys.exit(1)

print("\n✅ TEST FASE 2 PASADO: La señal CW sobrevivió intacta en todos los fragmentos reconectados.")
