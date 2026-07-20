#!/usr/bin/env python3
"""
probe_device.py
Script para detectar programáticamente los SDR conectados (Harogic u otros)
utilizando la API de SoapySDR en Python y devolviendo un JSON estructurado.

Debe ejecutarse dentro del entorno RF-Swift o a través del wrapper probe.sh.
"""

import sys
import json
import traceback

def get_range_dict(r):
    """Convierte un objeto SoapySDR.Range a un diccionario nativo"""
    try:
        return {"min": r.minimum(), "max": r.maximum(), "step": r.step()}
    except Exception:
        # En caso de que step no esté disponible
        return {"min": r.minimum(), "max": r.maximum()}

def probe():
    output = {
        "status": "unknown",
        "error_state": None,
        "message": "",
        "devices": []
    }
    
    # 1. ESTADO: Driver ausente (Falta la librería en el entorno)
    try:
        import SoapySDR
    except ImportError:
        output["status"] = "error"
        output["error_state"] = "Driver ausente"
        output["message"] = "SoapySDR module no encontrado en Python. El driver base está ausente."
        print(json.dumps(output, indent=2))
        sys.exit(1)

    try:
        devices = SoapySDR.Device.enumerate()
    except Exception as e:
        output["status"] = "error"
        output["error_state"] = "Error de enumeración"
        output["message"] = str(e)
        print(json.dumps(output, indent=2))
        sys.exit(1)
        
    harogic_devices = [d for d in devices if dict(d).get("driver") == "harogic"]
    
    # 2. ESTADO: Sensor no conectado
    if not harogic_devices:
        output["status"] = "error"
        output["error_state"] = "Sensor no conectado"
        output["message"] = "No se encontraron sensores Harogic en el bus USB."
        print(json.dumps(output, indent=2))
        sys.exit(1)

    # 3. Analizar capacidades del sensor
    for dev_kwargs in harogic_devices:
        dev_info = dict(dev_kwargs)
        
        # Intentamos abrir el dispositivo
        try:
            sdr = SoapySDR.Device(dev_kwargs)
        except Exception as e:
            err_str = str(e).lower()
            # 4. ESTADO: Calfile Invalido o Sensor Ocupado
            if "calfile" in err_str or "calibration" in err_str or "file" in err_str:
                state = "Calfile Invalido"
            elif "access" in err_str or "permission" in err_str or "busy" in err_str:
                state = "Sensor Ocupado o Sin Permisos"
            else:
                state = "Error de inicialización de Hardware"
                
            output["status"] = "error"
            output["error_state"] = state
            output["message"] = f"Fallo al abrir el sensor: {str(e)}"
            print(json.dumps(output, indent=2))
            sys.exit(1)
            
        try:
            # Extraer capacidades reales consultando al hardware
            freq_ranges = [get_range_dict(r) for r in sdr.getFrequencyRange(SoapySDR.SOAPY_SDR_RX, 0)]
            sample_rates = [get_range_dict(r) for r in sdr.getSampleRateRange(SoapySDR.SOAPY_SDR_RX, 0)]
            
            gain_range_obj = sdr.getGainRange(SoapySDR.SOAPY_SDR_RX, 0)
            gain_range = get_range_dict(gain_range_obj)

            dev_info["capabilities"] = {
                "frequency_ranges_hz": freq_ranges,
                "sample_rates_sps": sample_rates,
                "gain_range_db": gain_range
            }
            output["devices"].append(dev_info)
        except Exception as e:
            output["status"] = "error"
            output["error_state"] = "Error de lectura de capacidades"
            output["message"] = f"Error obteniendo capacidades: {str(e)}"
            print(json.dumps(output, indent=2))
            sys.exit(1)
            
    output["status"] = "success"
    output["error_state"] = "Ninguno"
    output["message"] = "Sensor detectado y capacidades mapeadas correctamente."
    output["devices_found"] = len(output["devices"])
    print(json.dumps(output, indent=2))
    sys.exit(0)

if __name__ == "__main__":
    probe()
