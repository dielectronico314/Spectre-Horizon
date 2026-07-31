import SoapySDR
import numpy as np

def test():
    sdr = SoapySDR.Device({"driver": "harogic"})
    rxStream = sdr.setupStream(SoapySDR.SOAPY_SDR_RX, SoapySDR.SOAPY_SDR_CS16)
    sdr.activateStream(rxStream)
    mtu = sdr.getStreamMTU(rxStream)
    
    # Use complex64 array (itemsize=8) but request CS16 format
    buff = np.zeros(mtu, np.complex64)
    
    sr = sdr.readStream(rxStream, [buff], mtu, timeoutUs=1000000)
    print(f"Format: CS16, Ret: {sr.ret}")
    
    # Check if the bytes look like float32 or int16
    raw_bytes = buff.tobytes()[:32]
    import struct
    floats = struct.unpack(f"<{len(raw_bytes)//4}f", raw_bytes)
    ints = struct.unpack(f"<{len(raw_bytes)//2}h", raw_bytes)
    print("As floats:", [round(f, 2) for f in floats[:8]])
    print("As ints:", ints[:16])
    
    sdr.deactivateStream(rxStream)
    sdr.closeStream(rxStream)

test()
