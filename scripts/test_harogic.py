import SoapySDR
import numpy as np

print("Buscando Harogic SDR...")
try:
    sdr = SoapySDR.Device({"driver": "harogic"})
    print("✅ Dispositivo Harogic encontrado!")
except Exception as e:
    print(f"❌ Error buscando dispositivo: {e}")
    exit(1)

print("Configurando Stream (1.95 MSps, 2.4 GHz)...")
sdr.setSampleRate(SoapySDR.SOAPY_SDR_RX, 0, 1.95e6)
sdr.setFrequency(SoapySDR.SOAPY_SDR_RX, 0, 2400e6)
sdr.setGain(SoapySDR.SOAPY_SDR_RX, 0, 40.0)

rxStream = sdr.setupStream(SoapySDR.SOAPY_SDR_RX, SoapySDR.SOAPY_SDR_CS16)
sdr.activateStream(rxStream)

print("Intentando leer datos...")
buff = np.zeros(131072, np.complex64)
buff_view = buff.view(np.int16)

try:
    sr = sdr.readStream(rxStream, [buff_view], 131072, timeoutUs=2000000)
    if sr.ret > 0:
        print(f"✅ ¡ÉXITO! Se leyeron {sr.ret} muestras del bus USB.")
    elif sr.ret == SoapySDR.SOAPY_SDR_TIMEOUT:
        print("❌ TIMEOUT: El dispositivo se inicializó pero no envió datos (Posible fallo USB/Hardware).")
    else:
        print(f"❌ ERROR: Código de retorno inusual: {sr.ret}")
finally:
    sdr.deactivateStream(rxStream)
    sdr.closeStream(rxStream)
