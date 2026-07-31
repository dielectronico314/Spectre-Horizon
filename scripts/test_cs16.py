import SoapySDR
import numpy as np

def test(dtype_str, buff_type, size):
    try:
        sdr = SoapySDR.Device({"driver": "harogic"})
        rxStream = sdr.setupStream(SoapySDR.SOAPY_SDR_RX, dtype_str)
        sdr.activateStream(rxStream)
        buff = np.zeros(size, buff_type)
        sr = sdr.readStream(rxStream, [buff], 32768, timeoutUs=1000000)
        print(f"Format: {dtype_str}, Buffer: {buff_type}, Ret: {sr.ret}")
        sdr.deactivateStream(rxStream)
        sdr.closeStream(rxStream)
    except Exception as e:
        print(f"Error with {dtype_str} and {buff_type}: {e}")

test(SoapySDR.SOAPY_SDR_CS16, np.complex64, 32768)
test(SoapySDR.SOAPY_SDR_CS16, np.int16, 32768*2)
