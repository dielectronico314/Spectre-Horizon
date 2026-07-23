# Diccionario de Datos: Contrato SigMF (v0.1)

El archivo `.sigmf-meta` es un estándar JSON adoptado en la industria SDR. Este documento define qué campos inyecta nuestro orquestador `capture_iq.py` y qué significan.

### Esquema Global (Nivel de Sesión)

La sección `global` describe las condiciones del entorno y del sensor al momento de la ejecución. Es inmutable para todos los bloques de la captura.

| Campo JSON | Tipo | Descripción | Obligatorio |
| :--- | :--- | :--- | :---: |
| `core:datatype` | string | El formato de los datos binarios `.iq`. Siempre será `cf32_le` (Complex Float 32-bit Little Endian) que representa las muestras IQ (In Phase / Quadrature) intercaladas. | ✅ |
| `core:sample_rate` | number | Velocidad de muestreo configurada en el SDR, medida en Muestras por Segundo (SPS). | ✅ |
| `core:hw` | string | Nombre o identificador del hardware capturador (Ej. `Harogic SDR`). | ✅ |
| `core:author` | string | Autor, nombre del script o pipeline responsable de crear el archivo. | ✅ |
| `core:version` | string | Versión interna de la herramienta de captura para trazabilidad de compatibilidad (Ej. `0.2.0`). | ✅ |

---

### Esquema de Capturas (Nivel de Bloque / Chunk)

La sección `captures` es un arreglo (array) que describe el tiempo, la frecuencia y la salud de un bloque IQ individual. En nuestra arquitectura, el arreglo contendrá exactamente un objeto.

| Campo JSON | Tipo | Descripción | Obligatorio |
| :--- | :--- | :--- | :---: |
| `core:sample_start` | integer | Índice de la primera muestra en este bloque. Normalmente `0` ya que dividimos los archivos físicamente en bloques individuales. | ✅ |
| `core:frequency` | number | La frecuencia central a la que estaba sintonizado el Harogic SDR, en Hertz (Hz). | ✅ |
| `core:datetime` | string | El *Timestamp* exacto (ISO-8601 UTC) en el que se grabó la primera muestra del bloque. | ✅ |
| `core:overflows` | integer | Contador de cuellos de botella (Overflows). Si es mayor a 0, significa que el disco duro fue muy lento y se perdieron muestras de RF en este bloque temporal. | ✅ |
| `telemetry:duration_sec` | number | Tiempo real (en segundos) que duró la grabación del bloque. | ✅ |
| `telemetry:throughput_mbps` | number | Tasa de escritura en disco duro real, medida en Megabytes por Segundo (MB/s). | ✅ |
| `telemetry:size_mb` | number | El tamaño exacto del bloque `.iq` que acompaña a este metadato. | ✅ |

---

### Validación Automática

Cualquier archivo `.sigmf-meta` puede (y debe) ser auditado mediante el comando `scripts/validate.sh` para confirmar que cumple al pie de la letra este diccionario de datos antes de ser consumido por un Dashboard o Base de Datos.
