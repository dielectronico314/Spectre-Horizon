import SoapySDR
import numpy as np

def test():
    try:
        sdr = SoapySDR.Device({"driver": "harogic"})
        rxStream = sdr.setupStream(SoapySDR.SOAPY_SDR_RX, SoapySDR.SOAPY_SDR_CS16)
        sdr.activateStream(rxStream)
        
        # Allocate larger buffer to prevent overflow
        buff = np.empty(32768 * 2, np.int32)
        print("Buffer bytes:", buff.nbytes)
        
        sr = sdr.readStream(rxStream, [buff], 32768, timeoutUs=1000000)
        print(f"Format: CS16, Ret: {sr.ret}")
        sdr.deactivateStream(rxStream)
        sdr.closeStream(rxStream)
    except Exception as e:
        print(f"Error: {e}")

test()
