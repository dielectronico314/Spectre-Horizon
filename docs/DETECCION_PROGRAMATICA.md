# Detección Programática del Sensor Harogic (Día 4)

## Objetivo
El objetivo de esta fase (Día 4) fue realizar la transición desde una validación de hardware manual (usando herramientas CLI como `SoapySDRUtil` o interfaces gráficas como `GQRX`) hacia una **detección programática y automatizada** mediante Python. Esto es un requisito fundamental para que futuras APIs o servicios backend puedan consultar el estado del hardware sin intervención humana.

## Componentes Desarrollados

Se crearon tres elementos principales en esta fase:

1. **`scripts/probe_device.py`**: El script núcleo en Python. Se ejecuta dentro del contenedor `mysdr` e interactúa directamente con la API C++ de SoapySDR mediante sus "bindings" (envolturas) de Python.
2. **`scripts/probe.sh`**: Un script envoltorio (wrapper) en Bash diseñado para el sistema host. Su función es inyectar el script de Python en el contenedor y, críticamente, **silenciar la salida de error estándar (stderr)**. Esto evita que los logs internos de inicialización de C++ contaminen la salida de datos.
3. **`rf-spectrum/data/sensor_capabilities.json`**: El archivo de salida estándar generado, el cual contiene la topología del hardware en formato JSON.

---

## Manejo de Estados y Tolerancia a Fallos

El script fue diseñado para no fallar silenciosamente, sino para identificar y reportar en JSON los 3 estados críticos de desconexión o falla:

1. **Driver Ausente (`Driver ausente`)**:
   - **Causa:** El contenedor o entorno de ejecución no tiene instalada la librería `SoapySDR` o el módulo base de Harogic (`libHarogicSupport.so`).
   - **Respuesta:** El script captura el `ImportError` e informa de la ausencia del driver.

2. **Sensor No Conectado (`Sensor no conectado`)**:
   - **Causa:** El bus USB no tiene el equipo Harogic conectado, o el contenedor fue arrancado sin los privilegios USB (`-s /dev/bus/usb -u 1`).
   - **Respuesta:** La función `SoapySDR.Device.enumerate()` devuelve una lista vacía. El script verifica que no hay IDs asociados al driver de Harogic.

3. **Calfile Inválido o Puerto Ocupado (`Calfile Invalido` / `Sensor Ocupado`)**:
   - **Causa:** El sensor está conectado, pero falló la inicialización (instanciación de `SoapySDR.Device()`). Esto suele deberse a que la carpeta `/usr/bin/CalFile` está vacía (faltan archivos de calibración obligatorios) o a que otro programa (`SAStudio4`) tiene el puerto USB bloqueado (`EBUSY`).
   - **Respuesta:** Se captura la excepción en tiempo de ejecución, analizando el string del error C++ para determinar la causa raíz.

---

## Mapeo de Capacidades Extraídas

El script logró consultar con éxito el hardware Harogic (Serie: `5746501400280003`) y extraer sus límites operativos reales. Estas capacidades quedan documentadas en el archivo JSON:

*   **Rango de Frecuencia (Frequency Range)**: 
    *   De **9 kHz** a **40 GHz** (9,000 Hz - 40,000,000,000 Hz).
*   **Velocidades de Muestreo (Sample Rates)**: 
    *   Soporta 8 etapas exactas de decimación en banda base.
    *   Máximo: **125 MSPS** (Megamuestras por segundo).
    *   Mínimo: **976.562 kSPS**.
*   **Ganancia (Gain Range)**: 
    *   Rango dinámico desde **-100 dB** hasta **+7 dB**.

## Uso

Cualquier sistema o microservicio puede consultar el hardware de forma segura y estructurada ejecutando el siguiente comando desde la raíz del proyecto:

```bash
./scripts/probe.sh
```

**Ejemplo de Salida Exitosa:**
```json
{
  "status": "success",
  "error_state": "Ninguno",
  "message": "Sensor detectado y capacidades mapeadas correctamente.",
  "devices_found": 1,
  "devices": [
    {
      "driver": "harogic",
      "label": "Harogic 5746501400280003",
      "serial": "5746501400280003",
      "capabilities": { ... }
    }
  ]
}
```
