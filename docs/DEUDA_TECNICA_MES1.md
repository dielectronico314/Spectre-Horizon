## Hardware/DSP
- fs real del Harogic: 1,953,125 Hz (no 1.95M nominal) — confirmado por 2 vías, aplicado desde Día 15+.
- LO leakage en offset=0 del centro de sintonía — presente en las 4 sesiones de 923MHz, filtrado del panel de destacados por band_name (string match "LoRa", no física real de offset).

## Configuración
- config/test_only/features_config_10events.json — cuarentenada tras contaminar 86 eventos falsos en el índice de producción (encontrado y purgado el Día 19).
- Tolerancia de deduplicación de 500kHz fija — no escala a anchos de banda mucho mayores (WiFi 20MHz).
- confianza_escala_db=10dB — satura en 1.0 para casi cualquier señal FM real, poco informativa ahí.
- margen_umbral_db default subido de 2.0 a 6.0dB tras el bug de falsos positivos en estrategia `temporal` — validar si alguna banda real con esa estrategia necesita override propio.

## Arquitectura
- run_servers.sh / puerto 8001 — confirmado su eliminación en la Sección 1.
- WeasyPrint opcional — fallback a impresión manual si no está instalado.
- Ring buffer SPSC (Día 12) — no soporta un segundo consumidor externo sin rediseño (relevante para integración futura con TETRA-Demod).

## Visual
- Dashboard funcional ejecutado y refactorizado a diseño WOW (completado el Día 20 por Claude y revisado contra especificación).

## Operativo
- 2 sesiones huérfanas benignas (previas al esquema session_*) — documentadas, no bloqueantes.
