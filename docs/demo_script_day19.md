# Guion de Demostración: Cenital RF (Día 19)

**Duración estimada:** 10-15 minutos
**Audiencia:** Ejecutivos y técnicos de alto nivel.
**Objetivo:** Demostrar la unificación del sistema (API + Dashboard + Motor SDR), la precisión determinista en la detección de anomalías y el flujo completo de recolección de evidencia forense.

---

## 1. Introducción y Estado del Sistema (2 mins)
*   **Acción:** Abrir el Dashboard en `http://localhost:8000/dashboard/`. Mostrar la pantalla principal de "Estado del Sensor".
*   **Narrativa:** 
    *   "Bienvenidos a Cenital RF. Lo que están viendo es el centro de comando unificado."
    *   "El sistema opera de forma completamente desatendida. Todo el procesamiento pesado de señales (DSP) y el motor de eventos corren en background."
    *   Mencionar que el sistema procesa gigabytes de espectro crudo (IQ) y los comprime en paquetes forenses ultra-ligeros.

## 2. El Terreno Físico: FM Comercial (3 mins)
*   **Acción:** Navegar a la pestaña "Sesiones" y abrir una de las sesiones de `106.5MHz` (por ejemplo, `session_20260723_093700_106.5MHz`). Mostrar el espectrograma 2D y el 3D interactivo.
*   **Narrativa:** 
    *   "Para probar el sistema en el mundo real, monitoreamos bandas de radio comercial."
    *   "El dashboard nos permite visualizar el espectro completo. Esta es una transmisión continua capturada por el sensor."
    *   "El motor de eventos extrae las características físicas (potencia, duración) de una transmisión viva sin abrumar la base de datos. Como pueden ver en el detalle, esta sesión continua extrae **exactamente 1 evento (`FM_106.5`), no decenas de falsos positivos fragmentados.** El sistema sabe cuándo empieza y cuándo termina la transmisión real."

## 3. Precisión Determinista: El Golden Dataset (5 mins)
*   **Acción:** Navegar a la pestaña "Eventos" y filtrar por "Golden Dataset" o mostrar directamente los eventos `CW_Tone` y `Synth_Burst`.
*   **Narrativa:**
    *   "El mundo real es ruidoso, pero para poder confiar en las mediciones, el motor debe extraer parámetros físicamente verificables."
    *   "Inyectamos un dataset sintético ('Golden Dataset') con dos señales de comportamiento matemáticamente predecible."
    *   **Mostrar `CW_Tone`:** "Inyectamos un tono continuo de 5.0 segundos. El sistema extrajo una duración de **4.999s** (pico de -13.61 dBFS)."
    *   **Mostrar `Synth_Burst`:** "Inyectamos un pulso sintético de 2.0 segundos exactos. El sistema extrajo **1.999s** (pico de -5.90 dBFS)."
    *   "Esta prueba confirma la calibración temporal del motor de eventos."

## 4. Evidencia Forense Inmutable (3 mins)
*   **Acción:** Hacer clic en el detalle del evento `CW_Tone` y abrir los enlaces de descarga de evidencia (JSON, PNG, CSV).
*   **Narrativa:**
    *   "Cuando el sistema detecta una anomalía, no solo genera una alerta. Construye un paquete de evidencia criptográficamente sellado."
    *   "Este paquete contiene el espectrograma, la metadata y los features crudos, listo para análisis experto posterior o cadena de custodia."

## 5. Cierre y Q&A (2 mins)
*   **Acción:** Volver al dashboard principal.
*   **Narrativa:** "Hoy tenemos un sistema robusto, determinista y listo para integrarse en producción. Gracias."

---

### *Nota para el Presentador (Bonus / Q&A)*
Si la audiencia técnica pregunta sobre **Artefactos o Falsos Positivos:**
*   Puedes mostrar el evento catalogado como `LoRa_923` en la sesión específica `session_20260804_115711_923.0MHz`.
*   **Explicación:** "El hardware tiene imperfecciones físicas, como fugas del oscilador local (LO Leakage). El motor registró este artefacto como un evento de alta energía (pico de **-11.43 dBFS**) y larga duración (**60.09s**). Sin embargo, gracias al paquete de evidencia, el operador humano puede observar que la señal tiene un **offset de frecuencia de 0 Hz** en el centro exacto de sintonía, y clasificarlo definitivamente como una anomalía interna del hardware. El sistema provee la evidencia física inmutable; el experto toma la decisión informada."
