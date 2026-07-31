#!/usr/bin/env python3
import sys
import json
import subprocess
from pathlib import Path

def main():
    print("🧪 Ejecutando Tests de Aceptación de Features (Día 13)")
    
    # Rutas
    npz_path = Path("/workspace/tests/day13_synthetic/test_burst_espectrograma.npz")
    config_path = Path("/workspace/config/features_config_relative.json")
    out_dir = Path("/workspace/tests/day13_synthetic")
    
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
    err_cw_pwr = abs(tone_band['potencia_media_dbfs'] - (-13.98))
    if err_cw_pwr > 0.5:
        print(f"❌ FALLA: Potencia media del Tono CW se sale de tolerancia. Error: {err_cw_pwr:.2f} dB")
        sys.exit(1)
    print("   ✅ ASSERT PASSED: Potencia CW vs teórico (±0.5 dB).")
    
    # 2MHz / 1024 bins = 1953.125 Hz por bin
    df = 1953.125
    print(f"   [Tono CW] BW reportado: {tone_band['bw_media_hz']:.1f} Hz (Δf = {df:.1f} Hz)")
    err_cw_bw = abs(tone_band['bw_media_hz'] - df)
    if err_cw_bw > 2 * df:
        print(f"❌ FALLA: BW del Tono CW se sale de tolerancia (±2 bins). Error: {err_cw_bw:.1f} Hz")
        sys.exit(1)
    print("   ✅ ASSERT PASSED: BW vs Δf (±2 bins).")
    
    print(f"   [Tono CW] SNR medio: {tone_band['snr_media_db']:.2f} dB")
    # Teórico SNR CW: Señal -13.98 dBFS. Piso de ruido por bin = -16.99 - 10*log10(1024) = -47.09 dBFS.
    # SNR teórico = 33.11 dB.
    err_cw_snr = abs(tone_band['snr_media_db'] - 33.11)
    if err_cw_snr > 1.0:
        print(f"❌ FALLA: SNR del Tono CW se sale de tolerancia (±1 dB). Error: {err_cw_snr:.2f} dB")
        sys.exit(1)
    print("   ✅ ASSERT PASSED: SNR CW vs teórico (±1 dB).")

    # Assert: BW tono puro debe ser << 10 kHz (máximo lóbulo Hann ~7.6 kHz)
    if tone_band['bw_media_hz'] > 10000:
        print(f"❌ FALLA: BW tono CW = {tone_band['bw_media_hz']:.1f} Hz (máximo ~7.6 kHz). Bandas se solapan o mal definidas.")
        sys.exit(1)
    
    # 2. Validar Burst (En la banda Synth_Burst, freq_low 150k a 250k, el burst está en 200k)
    # Esperamos duración = 2.0s
    burst_band = bands.get("Synth_Burst")
    if not burst_band:
        print("❌ Falla: No se encontró el resumen de la banda Synth_Burst (Burst)")
        sys.exit(1)
        
    print(f"   [Burst] Duración detectada: {burst_band['duracion_activa_s']:.2f}s (Esperada: 2.0s)")
    print(f"   [Burst] SNR medio: {burst_band['snr_media_db']:.2f} dB")
    # Teórico SNR Burst Medio: 
    # Ruido en la banda (100kHz) = -16.99 - 10*log10(2000/100) = -30.0 dBFS
    # Potencia Activa = -6.02 dBFS. SNR activo = 23.98 dB.
    # El SNR promediado sobre 5s (2s activo, 3s silencio) = (2 * 23.98 + 3 * 0) / 5 = 9.59 dB.
    err_burst_snr = abs(burst_band['snr_media_db'] - 9.59)
    if err_burst_snr > 1.0:
        print(f"❌ FALLA: SNR del Burst se sale de tolerancia (±1 dB). Error: {err_burst_snr:.2f} dB")
        sys.exit(1)
    print("   ✅ ASSERT PASSED: SNR Burst medio vs teórico (±1 dB).")
    
    print(f"   [Burst] BW medio: {burst_band['bw_media_hz']:.1f} Hz")
    err_burst_bw = abs(burst_band['bw_media_hz'] - df)
    if err_burst_bw > 2 * df:
        print(f"❌ FALLA: BW del Burst se sale de tolerancia (±2 bins). Error: {err_burst_bw:.1f} Hz")
        sys.exit(1)
    print("   ✅ ASSERT PASSED: BW vs Δf (±2 bins).")

    err_dur = abs(burst_band['duracion_activa_s'] - 2.0)
    if err_dur > 0.05:
        print(f"❌ FALLA: Duración del burst se sale de tolerancia. Error: {err_dur:.4f}s")
        sys.exit(1)
    print("   ✅ ASSERT PASSED: Duración exacta (±0.05s).")
        
    print(f"   [Burst] Pico máximo: {burst_band['pico_max_dbfs']:.2f} dBFS (Teórico ~ -6.02 dBFS)")
    
    # Tolerancia del pico ±1.5 dB (debido al scalloping loss de la ventana de Hann, que puede atenuar el pico hasta 1.42 dB si cae entre dos bins)
    err_pico = abs(burst_band['pico_max_dbfs'] - (-6.02))
    if err_pico > 1.5:
        print(f"❌ FALLA: Pico del burst se sale de tolerancia. Error: {err_pico:.2f} dB")
        sys.exit(1)
    print("   ✅ ASSERT PASSED: Pico máximo dentro de tolerancia de scalloping loss (±1.5 dB).")
    
    print(f"   [Burst] Potencia Media: {burst_band['potencia_media_dbfs']:.2f} dBFS")
    print("   ✅ NOTA: La potencia media promedia TODA the sesión (incluyendo los silencios). No representa la potencia del burst activo.")


    # Assert: SNR burst debe ser positivo y medible
    if burst_band['snr_media_db'] < 5:
        print(f"❌ FALLA: SNR burst debe ser >5 dB, es {burst_band['snr_media_db']:.2f} dB")
        sys.exit(1)

    print("✅ ¡Todos los tests de features han pasado!")
    
if __name__ == "__main__":
    main()
