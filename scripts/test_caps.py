import SoapySDR
try:
    sdr = SoapySDR.Device({"driver": "harogic"})
    print("Freq Range:", sdr.getFrequencyRange(SoapySDR.SOAPY_SDR_RX, 0))
    print("Sample Rates:", sdr.getSampleRateRange(SoapySDR.SOAPY_SDR_RX, 0))
    print("Gain Range:", sdr.getGainRange(SoapySDR.SOAPY_SDR_RX, 0))
except Exception as e:
    print("Error:", e)
