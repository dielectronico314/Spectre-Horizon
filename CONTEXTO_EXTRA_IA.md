# Contexto del Proyecto: Spectre-Horizon (Día 1 al 8)
## Para revisión de Inteligencia Artificial

Saludos, IA asistente. Este documento contiene el contexto de ingeniería completo del repositorio `Spectre-Horizon` para que puedas analizarlo, continuarlo o refactorizarlo sin perder el hilo arquitectónico.

### 1. Propósito del Proyecto
El objetivo de Spectre-Horizon es automatizar la captura de espectro de radiofrecuencia (RF) utilizando un analizador de espectro de hardware **Harogic SAN-400**, prescindiendo de su pesada interfaz gráfica original (SAStudio4) y operándolo en un entorno "headless" y altamente resiliente para despliegues de grado industrial.

### 2. Pila Tecnológica (Stack)
- **Host OS:** Ubuntu Linux.
- **Hardware:** Harogic SAN-400 (conectado vía USB 3.0).
- **Contenedor:** Toda la ingesta se ejecuta dentro del contenedor Docker `penthertz/rfswift_noble:sdr_full` (RF-Swift). El host no tiene librerías instaladas nativamente (para evitar el error `externally-managed-environment`).
- **Controlador API:** SoapySDR (Driver C++ embebido en el contenedor).
- **Lenguaje Principal:** Python 3.10+ (para la lógica de captura e ingesta).
- **Formatos:** Señal IQ pura en Complex Float 32-bit (`cf32_le`) y metadatos en estándar **SigMF v0.1**.

### 3. Arquitectura Resiliente (Lo más crítico)
El proyecto ha sido diseñado para sobrevivir a desconexiones físicas del hardware en caliente:
1. **Watchdog (`watchdog_usb.sh`):** Un demonio Bash en el host vigila los eventos del bus USB (`lsusb`). Si el SDR se desconecta físicamente y se vuelve a conectar, el watchdog lanza un `docker restart mysdr` para devolverle el acceso al bus `/dev/bus/usb` al contenedor.
2. **Wrapper (`capture.sh`):** Un script Bash en el host que lanza el script Python en el contenedor mediante un bucle `while true; do docker exec ...; done`. Así, si el contenedor se reinicia, el wrapper vuelve a lanzar el script de captura sin que la sesión principal muera.
3. **Chunking Temporizado (`capture_iq.py`):** Los archivos IQ nunca se graban como un solo monolito gigante. Se dividen en bloques de $N$ segundos (ej. 60s) para evitar la pérdida total de una sesión de 24h si el disco se corrompe.

### 4. Contrato de Metadatos (SigMF)
Toda captura binaria `.iq` viene acompañada de un archivo JSON `.sigmf-meta`. Hemos adoptado una estructura estricta (validada por `validate_meta.py` y `sigmf_v0.1.schema.json`) que inyecta:
- Hash criptográfico `SHA256` (Cadena de custodia de la evidencia IQ).
- Identificadores de Hardware (CalFile), Versión de Software, Ganancia, Antena, y Coordenadas geográficas.
- Telemetría: Uso de Disco (MB), Throughput (MB/s), y Cuellos de botella (`overflows`).

### 5. Estado Actual (Hasta el Día 8)
- El entorno está estable.
- La ingesta sobrevive a tirones de cable.
- El contrato SigMF es obligatorio y funcional (100% test passing).
- Puedes comenzar a desarrollar la Fase 2 (Día 9+): Extracción matemática de eventos sobre los archivos `.iq` o el despliegue del Dashboard API.
