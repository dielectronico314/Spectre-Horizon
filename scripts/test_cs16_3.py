import SoapySDR
import numpy as np

def test():
    try:
        sdr = SoapySDR.Device({"driver": "harogic"})
        rxStream = sdr.setupStream(SoapySDR.SOAPY_SDR_RX, SoapySDR.SOAPY_SDR_CS16)
        sdr.activateStream(rxStream)
        mtu = sdr.getStreamMTU(rxStream)
        print("MTU:", mtu)
        buffer_size = mtu
        # Allocate exact size
        buff = np.zeros(buffer_size * 2, np.int16)
        print("Buffer bytes:", buff.nbytes)
        
        sr = sdr.readStream(rxStream, [buff], buffer_size, timeoutUs=1000000)
        print(f"Format: CS16, Ret: {sr.ret}")
        sdr.deactivateStream(rxStream)
        sdr.closeStream(rxStream)
    except Exception as e:
        print(f"Error: {e}")

test()
