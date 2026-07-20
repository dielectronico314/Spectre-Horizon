import sys, json
try:
    import SoapySDR
    sdr = SoapySDR.Device({"driver": "harogic"})
    r = sdr.getFrequencyRange(SoapySDR.SOAPY_SDR_RX, 0)[0]
    print(json.dumps({"min": r.minimum(), "max": r.maximum()}))
except Exception as e:
    print(e)
