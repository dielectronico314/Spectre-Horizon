# Technical Report: Harogic Sensor Hardware Baseline (July 16)

## 1. Hardware Setup & Connection
- **Action**: Connected the Harogic sensor and its corresponding antenna to the designated test computer.
- **Status**: Successfully recognized by the system.
- **Device Details** (from logs):
  - **Model**: 94
  - **UID**: 0x5746501400280003

## 2. SAStudio Verification
- **Application Startup**: 
  - Overcame a permission issue where a previous `root` instance blocked the sensor. 
  - **Fix applied**: Modified `app.sh` to gracefully request privileges via `pkexec` when needed and created a global terminal alias (`sastudio`) for rapid launching.
- **Sensor Detection**: The sensor was successfully detected by SAStudio4 upon startup.
- **Calibration File**: CalFile loaded successfully on initialization.
- **Live Signal Observation**: Verified the presence of stable live signals, primarily focusing on the 2.4 GHz WiFi band during this initial test.

## 3. Stability Observation
- **Action**: Monitored the real-time spectrum using the spectrometer for a continuous 15-minute period.
- **Result**: The signal remained stable with no unexpected drops or hardware disconnections. The system processed the real-time data effectively without crashing.

## 4. Basic Measurements (Baseline Registration)
Based on the default configuration registered by the software during the connection:
- **Frequency SPAN**: ~40 GHz (Start: 8 kHz, Stop: 40.02 GHz)
- **Center Frequency**: 2.41 GHz
- **RBW (Resolution Bandwidth)**: 300 kHz
- **VBW (Video Bandwidth)**: 3 MHz
- **Analysis Bandwidth (Sample Rate)**: ~46.38 MHz
- **Trace Points**: 4000
- **Temperature**: *(Nominal / Registered during the 15-minute stress test)*

## 5. Next Steps
- Continue logging long-term stability.
- Document any specific anomalies in the 2.4 GHz and 5 GHz bands if utilizing the sensor for WiFi analysis.
