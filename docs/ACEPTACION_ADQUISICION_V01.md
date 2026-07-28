# Acta de Aceptación: Capa de Adquisición v0.1

**Fecha de Ejecución:** 28 de Julio de 2026
**Responsable Técnico:** Diego (Usuario) / Antigravity (IA)
**Hardware:** Harogic SAN-400 (S/N: 5746501400280003)
**Frecuencia Central:** 2400.0 MHz (Banda WiFi)
**Tasa de Muestreo:** 1.953 MS/s (CS16 Native)

---

## 1. Resumen Ejecutivo
El presente documento certifica la aprobación técnica del bloque de adquisición del proyecto Spectre-Horizon. Se sometió el hardware y software a una prueba de estrés continua de **60 minutos**, la cual incluyó desconexiones inducidas de forma deliberada. El sistema superó con éxito todas las métricas de tolerancia a fallos.

## 2. Resultados de las Pruebas

### A. Prueba de Larga Duración (60 Minutos)
- **Bloques Capturados:** 88 bloques totales.
- **Tolerancia Térmica:** APROBADO (El sensor mantuvo la captura sin degradación perceptible por 1 hora completa).
- **Integridad de Datos:** APROBADO (Todos los bloques superaron el Hash SHA256 criptográfico).
- **Validación SigMF:** APROBADO (Cero violaciones del contrato estricto v0.1).

### B. Prueba de Recuperación por Interrupción (Watchdog)
- **Simulación:** Desconexión manual del bus USB al minuto 30.
- **Comportamiento Esperado:** Detección de pérdida de stream, pausa controlada, y re-activación de un nuevo hilo de captura.
- **Resultado:** APROBADO. El script cerró limpiamente el bloque previo (`session_...084541`), esperó la reconexión, y generó automáticamente una nueva sesión (`session_...091641`) retomando el muestreo ininterrumpido.

### C. Prueba de Replay Offline (Bipartición)
- **Simulación:** Se inyectó un bloque resultante de esta prueba al motor `replay.sh`.
- **Resultado:** APROBADO. El motor emuló correctamente el tiempo real leyendo la metadata `core:sample_rate` y confirmó que el stream de datos IQ no estaba corrupto, probando que el procesamiento agnóstico es viable.

---

## 3. Limitaciones Conocidas (Defectos No Bloqueantes)
Durante la prueba se registraron las siguientes limitaciones que deberán tenerse en cuenta para futuras arquitecturas, pero que **no impiden** el avance hacia la capa de procesamiento (Día 11):

1. **Fragmentación de Sesión por Watchdog:** Cuando ocurre una desconexión, el Watchdog crea una carpeta de sesión completamente nueva en lugar de continuar en la original. Esto obligará al pipeline de análisis a monitorear múltiples carpetas si se desea procesar un día entero.
2. **Uso de Espacio en Disco:** A 1.953 MS/s, 1 hora de captura requiere bastante espacio de almacenamiento. El sistema actual asume que hay un disco duro SSD dedicado. Se recomienda programar una rutina de limpieza (`cron`) que elimine archivos procesados si se deja 24/7.
3. **Restricción de Contenedor:** Al requerir acceso de bajo nivel al hardware (`--privileged -v /dev/bus/usb`), escalar este componente de adquisición a entornos no Linux (o Kubernetes estricto) requerirá ajustes en los permisos de los dispositivos.

## 4. Veredicto Final

**ESTADO: [✅] APROBADO**

El sistema cuenta con datos de 1 hora, un sistema de Replay funcional para desarrollo offline, y tolerancia a fallas en vivo. La capa de Adquisición está formalmente certificada. Se autoriza el inicio del desarrollo de la **Capa de Procesamiento Espectral (Días 11-12)**.
