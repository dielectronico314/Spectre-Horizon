#!/usr/bin/env python3
import sys
import json
import subprocess
from pathlib import Path

def main():
    print("🧪 Ejecutando Tests de Aceptación de Features (Día 13)")
    
    # Rutas
    npz_path = Path("/workspace/tests/day13_features/test_burst_espectrograma.npz")
    config_path = Path("/workspace/config/features_config.json")
    out_dir = Path("/workspace/tests/day13_features")
    
    if not npz_path.exists():
        print(f"❌ Error: Falta el archivo {npz_path}")
        sys.exit(1)
        
    # Extraer features
    print("   Corriendo extract_features.py...")
    result = subprocess.run([
        "python3", "/workspace/scripts/extract_features.py",
        str(npz_path), "--config", str(config_path), "--out-dir", str(out_dir)
    ], capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ Error al extraer features:\n{result.stderr}")
        sys.exit(1)
        
    # Leer el resumen generado
    summary_path = out_dir / "resumen_test_burst_espectrograma.json"
    with open(summary_path, 'r') as f:
        summary = json.load(f)
        
    bands = { b["band_name"]: b for b in summary }
    
    # 1. Validar Tono CW (En la banda CW_Tone)
    tone_band = bands.get("CW_Tone")
    if not tone_band:
        print("❌ Falla: No se encontró el resumen de la banda CW_Tone (Tono CW)")
        sys.exit(1)

    print(f"   [Tono CW] Potencia media: {tone_band['potencia_media_dbfs']:.2f} dBFS")
    print(f"   [Tono CW] BW reportado: {tone_band['bw_media_hz']:.1f} Hz (máximo físico ~7.6 kHz)")
    print(f"   [Tono CW] SNR medio: {tone_band['snr_media_db']:.2f} dB")

    # Assert: BW tono puro debe ser << 10 kHz (máximo lóbulo Hann ~7.6 kHz)
    if tone_band['bw_media_hz'] > 10000:
        print(f"❌ FALLA: BW tono CW = {tone_band['bw_media_hz']:.1f} Hz (máximo ~7.6 kHz). Bandas se solapan o mal definidas.")
        sys.exit(1)

    # Assert: SNR CW debe ser alto (tono continuo puro)
    if tone_band['snr_media_db'] < 25:
        print(f"❌ FALLA: SNR tono CW debe ser >25 dB, es {tone_band['snr_media_db']:.2f} dB")
        sys.exit(1)
    
    # 2. Validar Burst (En la banda Synth_Burst, freq_low 150k a 250k, el burst está en 200k)
    # Esperamos duración = 2.0s
    burst_band = bands.get("Synth_Burst")
    if not burst_band:
        print("❌ Falla: No se encontró el resumen de la banda Synth_Burst (Burst)")
        sys.exit(1)
        
    print(f"   [Burst] Duración detectada: {burst_band['duracion_activa_s']:.2f}s (Esperada: 2.0s)")
    print(f"   [Burst] SNR medio: {burst_band['snr_media_db']:.2f} dB")
    print(f"   [Burst] BW medio: {burst_band['bw_media_hz']:.1f} Hz")

    err_dur = abs(burst_band['duracion_activa_s'] - 2.0)
    if err_dur > 0.05:
        print(f"❌ FALLA: Duración del burst se sale de tolerancia. Error: {err_dur:.4f}s")
        sys.exit(1)

    print(f"   [Burst] Pico máximo: {burst_band['pico_max_dbfs']:.2f} dBFS (Teórico ~ -6.02 dBFS)")

    err_pico = abs(burst_band['pico_max_dbfs'] - (-6.02))
    if err_pico > 1.5:
        print(f"❌ FALLA: Pico del burst se sale de tolerancia. Error: {err_pico:.2f} dB")
        sys.exit(1)

    # Assert: SNR burst debe ser positivo y medible
    if burst_band['snr_media_db'] < 5:
        print(f"❌ FALLA: SNR burst debe ser >5 dB, es {burst_band['snr_media_db']:.2f} dB")
        sys.exit(1)

    print("✅ ¡Todos los tests de features han pasado!")
    
if __name__ == "__main__":
    main()
