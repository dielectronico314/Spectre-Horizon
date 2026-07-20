# Estado Funcional - Captura IQ (Día 5)

Basado en los criterios formales de aceptación del Día 5, el siguiente documento detalla el estado actual del script `scripts/capture_iq.py` y las brechas que faltan por cubrir para alcanzar el 100% de cumplimiento.

## 1. Configuración parametrizable 
- **Estado:** ✅ Completado
- **Funcionalidad:** El script utiliza `argparse` y recibe exitosamente `--freq`, `--rate`, `--gain`, y `--duration`. Estos parámetros se inyectan dinámicamente al hardware a través de la API nativa de SoapySDR (CF32).

## 2. Capturar 60 segundos de IQ
- **Estado:** ✅ Completado (Capacidad demostrada)
- **Funcionalidad:** El bucle `while` está anclado a la duración real (`time.time()`). Se ha demostrado que puede capturar ráfagas sin corromper memoria, lo que permite capturas de 60 segundos o más enviando `--duration 60`.

## 3. Guardar IQ + metadata en una carpeta de sesión
- **Estado:** ⚠️ Parcialmente Completado (Brecha detectada)
- **Funcionalidad Actual:** Los archivos se guardan correctamente (`.iq` y `.sigmf-meta`) en `rf-spectrum/data/samples/`.
- **Qué falta:** El plan exige que se guarden dentro de una *carpeta de sesión individual* (por ejemplo, `rf-spectrum/data/samples/session_20260720_1535/`). Actualmente se guardan todos sueltos en el directorio raíz de `samples/`.

## 4. Calcular tamaño, duración y muestras
- **Estado:** ✅ Completado
- **Funcionalidad:** Al finalizar la captura o al interrumpirse, el script calcula e imprime con precisión el tamaño en MB, el tiempo real transcurrido y la sumatoria exacta de muestras obtenidas usando el bloque `sr.ret`.

## 5. Registrar overflows o pérdidas
- **Estado:** ⚠️ Parcialmente Completado (Brecha detectada)
- **Funcionalidad Actual:** El script intercepta el código de hardware `SOAPY_SDR_OVERFLOW` y lanza una alerta visual en la terminal.
- **Qué falta:** Actualmente no se están sumando cuántas veces ocurrió un overflow, ni se está registrando este número dentro del archivo JSON de Metadata final. Para cumplir la planificación, el metadata debe incluir un campo `overflows_count`.

## 6. Comando de detención segura
- **Estado:** ✅ Completado
- **Funcionalidad:** Se implementó una captura del evento de teclado (`KeyboardInterrupt` / Ctrl+C). Al activarse, rompe el bucle ordenadamente, cierra la tubería de hardware (`deactivateStream` y `closeStream`) y guarda todo el progreso hasta el segundo en el que se detuvo sin corromper el archivo binario.

---

### Resumen de Trabajo Pendiente para Cerrar el Día 5
Para cumplir con el criterio de cierre exacto, debemos hacer **3 ajustes menores**:
1. Modificar el script para que genere una subcarpeta (ej. `session_106MHz_hhmmss`) y guarde ahí los dos archivos.
2. Crear un contador de `overflows = 0`, incrementarlo en la alerta, e insertarlo en el JSON de Metadata.
3. Hacer la corrida final de demostración de 60 segundos (ejecutar `--duration 60`).
