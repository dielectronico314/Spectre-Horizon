## Hardware/DSP
- fs real del Harogic: 1,953,125 Hz (no 1.95M nominal) — confirmado por 2 vías, aplicado desde Día 15+.
- LO leakage en offset=0 del centro de sintonía — presente en las 4 sesiones de 923MHz, filtrado del panel de destacados por band_name (string match "LoRa", no física real de offset).
- Overhead de inicialización: El parámetro `--duration` solicitado incluye tiempo de inicialización de bus USB y sintonización. La señal útil capturada es consistentemente 2-5s menor que el tiempo de reloj total. Este es un comportamiento esperado del hardware y no una pérdida aleatoria de muestras.

## Configuración
- config/test_only/features_config_10events.json — cuarentenada tras contaminar 86 eventos falsos en el índice de producción (encontrado y purgado el Día 19).
- Tolerancia de deduplicación de 500kHz fija — no escala a anchos de banda mucho mayores (WiFi 20MHz).
- confianza_escala_db=10dB — satura en 1.0 para casi cualquier señal FM real, poco informativa ahí.
- margen_umbral_db default subido de 2.0 a 6.0dB tras el bug de falsos positivos en estrategia `temporal` — validar si alguna banda real con esa estrategia necesita override propio.

## Arquitectura
- run_servers.sh / puerto 8001 — confirmado su eliminación en la Sección 1.
- `start_services.sh` no detecta código desactualizado en el proceso ya corriendo — su idempotencia (pgrep) asume que si el proceso existe está bien. Cualquier deploy nuevo necesita matar el proceso viejo explícitamente antes de arrancar, de lo contrario sirve código huérfano.
- WeasyPrint opcional — fallback a impresión manual si no está instalado.
- Ring buffer SPSC (Día 12) — no soporta un segundo consumidor externo sin rediseño (relevante para integración futura con TETRA-Demod).
- Riesgo de API (Endpoint `/events/{event_id}`): El endpoint asume unicidad global de `event_id`. Si dos capturas generan eventos con bytes idénticos (ej. un experimento de copiado manual, o silencio absoluto duplicado), el API devolverá la evidencia del primero que encuentre. Reparar en el Mes 2 anidando bajo `/sessions/{session_id}/events/{event_id}`.
- Riesgo de Estado Volátil (Background Worker): El endpoint `/api/v1/captures` almacena el progreso de las capturas en un diccionario en memoria (`JOBS = {}`). Si el servidor uvicorn se reinicia en medio de un job, el estado se pierde irremediablemente y el frontend hará polling a un `job_id` inexistente (404). Para producción futura, migrar a Redis o tabla SQLite persistente.

## Visual
- Dashboard funcional ejecutado y refactorizado a diseño WOW (completado el Día 20 por Claude y revisado contra especificación).

## Operativo
- 2 sesiones huérfanas benignas (previas al esquema session_*) — documentadas, no bloqueantes.
