# Registro de Limitaciones y Deuda Técnica Conocida

Este documento rastrea desviaciones físicas, de hardware o de software descubiertas durante las pruebas empíricas, que se asumen como limitaciones aceptadas para el alcance actual del proyecto pero que requieren trazabilidad formal.

## 1. Tasa de Muestreo (Sample Rate) del SDR vs Readback SDK
* **Fecha de Registro:** Día 13 (Validación de Hardware en Tiempo Real)
* **Componente:** `SoapyHarogic` (Driver C++)
* **Descripción:** El SDK/Driver del Harogic no expone una lectura inversa (*readback*) del reloj de hardware tras aplicar el factor de decimación. La función `getSampleRate()` del driver es un eco ciego que simplemente devuelve el último valor configurado (`_sample_rate = rate`), sin comprobar qué tasa asumió realmente el hardware.
* **Estado Actual:** El software asume ingenuamente la tasa nominal (`fs = 1.95 MSps`). Basado en la deriva observada durante un Soak Test de 37 minutos (delta de `+3.6s` en tiempo de reloj de pared vs tiempo simulado), existe un error sistemático estimado del **~0.16%** en el reloj de muestreo.
* **Impacto Aceptado (Mes 1):** 
  - **Frecuencia:** Error de ~1.5 kHz en los bordes del span (`fs/2 × 0.16%`). Inofensivo para el Motor de Eventos, ya que opera con bandas anchas y márgenes de potencia.
  - **Tiempo:** Deriva de ~2.3 minutos/día. Irrelevante porque el alcance de este mes no incluye correlación cruzada contra sistemas de inteligencia externos.
* **Resolución Pendiente (Post-Mes 1):** No hardcodear valores "adivinados" de la hoja de datos. Requiere **calibración absoluta:** Inyectar una señal de frecuencia 100% precisa (ej. piloto estéreo FM a 19.000 kHz) por minutos, medir el error de desplazamiento en el bin de FFT y calcular el `fs` real del oscilador.
