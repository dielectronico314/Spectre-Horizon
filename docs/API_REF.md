# Referencia de la API (Día 16)

La API FastAPI de Spectre-Horizon está diseñada para servir como un middleware seguro, rápido e indexado para la lectura de eventos de radiofrecuencia (SDR) empacados criptográficamente.

## Decisiones Arquitectónicas

1. **Separación de Responsabilidades:**
   - La API **nunca** calcula hashes, ni detecta eventos, ni procesa señales IQ en tiempo real. 
   - El Indexador Batch (`scripts/build_index.py`) se encarga del trabajo pesado de recolectar los paquetes de evidencia (`manifest.json` y metadatos) en una base de datos `index.sqlite` que sirve para realizar búsquedas O(1) veloces y paginadas.

2. **Seguridad contra Path Traversal:**
   - Para descargar un archivo de evidencia se utiliza el endpoint: `/events/{event_id}/evidence/{filename:path}`.
   - Todo archivo solicitado se filtra mediante un estricto *whitelist*:
     `manifest.json`, `resumen.md`, `espectrograma_evento.png`, `evento.sigmf-data`, `evento.sigmf-meta`, `features_evento.csv`.
   - La base del directorio se resuelve de la base de datos segura y se verifica contra `is_relative_to(DATA_ROOT)`. Si el atacante inyecta `../../../etc/passwd`, es bloqueado y se emite un error `404` limpio por seguridad perimetral.

3. **Status del Sensor (`/sensor/status`):**
   - Este endpoint está diseñado para un contexto analítico asíncrono, no sincrónico-vivo.
   - Retorna la **última sesión** escaneada, no necesariamente un flujo en directo. 
   - El flag `en_vivo` (por ahora en `false`) servirá en futuras arquitecturas para comprobar si un `stream_processor` activo está reportando su latido de vida (`live.pid`).

4. **Tratamiento de Fechas Forenses:**
   - La columna `start_datetime` utilizada en los filtros por fecha (ej. `GET /events?desde=...`) se extrae **siempre** de los metadatos `core:datetime` del SigMF original (hora UTC). Nunca se basa en la fecha de modificación del archivo o fecha de ejecución de los scripts.

## Generación Automática
Toda la documentación REST interactiva y modelos de Pydantic pueden visualizarse localmente levantando el servidor:
```bash
docker exec harogic_final uvicorn app.api.main:app --host 0.0.0.0 --port 8000
```
Y navegando a `http://localhost:8000/docs`.
