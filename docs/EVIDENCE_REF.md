# Referencia de Evidencia Forense (EVIDENCE_REF)

Spectre-Horizon incluye un empaquetador de evidencia diseñado bajo estándares forenses para auditoría de eventos de radiofrecuencia. 

## Garantías Criptográficas y Matemáticas
El paquete de evidencia (`data/evidence/<event_id>`) ofrece las siguientes garantías:

1. **Unicidad de ID**: Los IDs de los eventos están atados al Hash SHA-256 de la captura en crudo original (ej. `016e125b2f58_FM_Sub1_0001`). No hay colisiones de IDs entre distintas sesiones.
2. **Autocontención**: El corte de IQ (`evento.sigmf-data`) extraído con `memmap` contiene la señal electromagnética exacta de la ventana de detección, y está acompañado de su propio `.sigmf-meta` para reproducibilidad en GNURadio u otros programas DSP.
3. **Reproducibilidad Matemática (Nivel 3)**: El bloque binario `evento.sigmf-data` garantiza reproducir exactamente el mismo Espectrograma y las mismas mediciones de Potencia/SNR si se pasa por el pipeline original (tolerancia `Δ=0.0 dB`).
4. **Firmas de Algoritmos**: El `manifest.json` sella no solo los resultados de los archivos CSV o imágenes, sino los hashes SHA-256 de los *scripts fuente en Python* usados durante la generación, asegurando que el modelo de decisión matemática no fue alterado furtivamente.

## Estructura del Paquete
```
data/evidence/<event_id>/
  ├── manifest.json              # Hashes SHA-256, Configuración Resuelta y Metadata
  ├── resumen.md                 # Resumen analítico legible por un humano
  ├── espectrograma_evento.png   # Render de la cascada (waterfall) del evento
  ├── evento.sigmf-data          # Slice crudo de muestras (CF32/CI16)
  ├── evento.sigmf-meta          # Metadata SigMF del slice con el padding anotado
  └── features_evento.csv        # Fragmento del CSV de las características espectrales
```

## Limitaciones
- El archivo `.sigmf-data` recortado tiene exactamente el mismo sample rate y offset que el archivo de banda ancha original. No es una sub-banda filtrada; contiene todas las demás señales coexistentes en ese instante de tiempo.
- La trazabilidad (Nivel 2 de Auditoría) requiere que la captura original de 1GB siga existiendo en el disco en el momento de auditar para confirmar el hash de origen.
