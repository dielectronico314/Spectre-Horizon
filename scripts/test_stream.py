import SoapySDR
import numpy as np
import time
sdr = SoapySDR.Device({"driver": "harogic"})
rxStream = sdr.setupStream(SoapySDR.SOAPY_SDR_RX, SoapySDR.SOAPY_SDR_CF32)
mtu = sdr.getStreamMTU(rxStream)
sdr.activateStream(rxStream)
buff = np.zeros(32768, np.complex64)
sr = sdr.readStream(rxStream, [buff], 32768, timeoutUs=1000000)
print("Read:", sr.ret)
sdr.deactivateStream(rxStream)
sdr.closeStream(rxStream)
