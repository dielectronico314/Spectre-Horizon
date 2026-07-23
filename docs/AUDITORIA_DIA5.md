# Estado Funcional - Captura IQ (Día 5)

Basado en los criterios formales de aceptación del Día 5, el siguiente documento detalla el estado actual del script `scripts/capture_iq.py` y las brechas que faltan por cubrir para alcanzar el 100% de cumplimiento.

## 1. Configuración parametrizable 
- **Estado:** ✅ Completado
- **Funcionalidad:** El script utiliza `argparse` y recibe exitosamente `--freq`, `--rate`, `--gain`, y `--duration`. Estos parámetros se inyectan dinámicamente al hardware a través de la API nativa de SoapySDR (CF32).

## 2. Capturar 60 segundos de IQ
- **Estado:** ✅ Completado (Capacidad demostrada)
- **Funcionalidad:** El bucle `while` está anclado a la duración real (`time.time()`). Se ha demostrado que puede capturar ráfagas sin corromper memoria, lo que permite capturas de 60 segundos o más enviando `--duration 60`.

## 3. Guardar IQ + metadata en una carpeta de sesión
- **Estado:** ✅ Completado
- **Funcionalidad:** El script ahora crea dinámicamente subcarpetas únicas por captura usando la sintaxis `session_YYYYMMDD_HHMMSS_FREQMHz/`. Tanto el archivo binario `.iq` como el contrato `.sigmf-meta` se depositan juntos y acoplados dentro de esta sesión aislada.

## 4. Calcular tamaño, duración y muestras
- **Estado:** ✅ Completado
- **Funcionalidad:** Al finalizar la captura o al interrumpirse, el script calcula e imprime con precisión el tamaño en MB, el tiempo real transcurrido y la sumatoria exacta de muestras obtenidas usando el bloque `sr.ret`.

## 5. Registrar overflows o pérdidas
- **Estado:** ✅ Completado
- **Funcionalidad:** El script intercepta activamente los códigos de error del hardware (como `SOAPY_SDR_OVERFLOW`). Mantiene un conteo continuo de las ráfagas perdidas por saturación de RAM, emite alertas en pantalla, y lo más importante: inyecta el total final en el parámetro `"core:overflows"` del contrato SigMF de la captura.

## 6. Comando de detención segura
- **Estado:** ✅ Completado
- **Funcionalidad:** Se implementó una captura del evento de teclado (`KeyboardInterrupt` / Ctrl+C). Al activarse, rompe el bucle ordenadamente, cierra la tubería de hardware (`deactivateStream` y `closeStream`) y guarda todo el progreso hasta el segundo en el que se detuvo sin corromper el archivo binario.

---

### Resumen Final de Cumplimiento (Día 5)
🎉 **ESTADO: 100% COMPLETADO Y CERRADO**

Todos los criterios formales dictados para la obtención y empaquetado de la primera captura IQ binaria han sido satisfechos. Como prueba de aceptación final, se ejecutó una corrida ininterrumpida de 60 segundos sobre la frecuencia de *107.3 MHz*, la cual arrojó cero (0) overflows y demostró una estabilidad absoluta en la tubería `CF32` generando un archivo íntegro de casi 1 Gigabyte de información de espectro, acompañado de su respectivo contrato SigMF. 

El repositorio ha sido enlazado a GitHub con éxito, dotándolo además de una portada técnica robusta. Estamos listos para avanzar al Día 6 (Escaneo en Banda Wi-Fi).
