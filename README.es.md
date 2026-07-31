<div align="center">

  # Spectre-Horizon
  
  **Pipeline Automatizado de Conciencia Espectral para Sensores SDR Harogic.**
  
  [![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
  [![Docker](https://img.shields.io/badge/Docker-RF--Swift-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)
  [![SoapySDR](https://img.shields.io/badge/SoapySDR-API-success.svg)](#)
  [![License](https://img.shields.io/badge/License-MIT-green.svg)](#)
  
  <br/>
  <img src="assets/san-400_01-1.png" alt="Harogic SAN-400 Spectrum Analyzer" width="600"/>
  <br/>
  <br/>

  *Un puente de software robusto para capturar, procesar, analizar y decidir sobre espectro electromagnético de grado industrial utilizando Python, Docker y SigMF.*
</div>

---

## 📖 Índice

- [Resumen del Proyecto](#-resumen-del-proyecto)
- [Arquitectura del Sistema](#-arquitectura-del-sistema)
- [Watchdog y Tolerancia a Fallos](#️-watchdog-y-tolerancia-a-fallos)
- [Requisitos de Hardware](#️-requisitos-de-hardware)
- [Dependencias Externas](#-dependencias-externas-y-descargas)
- [Instalación y Despliegue](#-instalación-y-despliegue)
- [Uso y Comandos](#-uso-y-comandos)
- [Estructura de Datos (SigMF)](#-estructura-de-datos-sigmf)
- [Estructura del Proyecto](#-estructura-del-proyecto)
- [Roadmap (Plan de 20 Días)](#-roadmap-plan-de-20-días)

---

## 🎯 Resumen del Proyecto

**Spectre-Horizon** es un pipeline completo de conciencia espectral — desde la captura de señal RF cruda hasta la generación de alertas tácticas — construido para sensores SDR Harogic operando dentro de una arquitectura basada en Docker.

Nació de la necesidad de desvincular la captura de espectro de las interfaces gráficas pesadas y manuales (como SAStudio4 o GQRX), permitiendo una captura automatizada y parametrizable (headless). El sistema no solo captura: **mide, evalúa y decide**, produciendo inteligencia procesable — no solo gráficas bonitas.

---

## 🏗 Arquitectura del Sistema

Spectre-Horizon está diseñado como un **pipeline de cuatro capas** donde cada capa está completamente desacoplada de las demás. Los datos fluyen hacia abajo desde el hardware hasta la inteligencia, mientras que la configuración fluye lateralmente a través de contratos JSON — lo que significa que **no se necesita modificar ni una sola línea de código Python** para apuntar a una nueva banda de frecuencia.

```mermaid
flowchart TB
    classDef hardware fill:#1a1a2e,stroke:#00ffcc,stroke-width:2px,color:#e0e0e0
    classDef host fill:#16213e,stroke:#e94560,stroke-width:2px,color:#e0e0e0
    classDef docker fill:#0f3460,stroke:#00b4d8,stroke-width:2px,color:#e0e0e0
    classDef python fill:#306998,stroke:#ffd43b,stroke-width:2px,color:#fff
    classDef config fill:#533483,stroke:#e94560,stroke-width:2px,color:#e0e0e0
    classDef storage fill:#1b1b2f,stroke:#ff6b6b,stroke-width:2px,color:#e0e0e0
    classDef alert fill:#e94560,stroke:#ffffff,stroke-width:2px,color:#fff
    classDef bash fill:#2d6a4f,stroke:#95d5b2,stroke-width:2px,color:#fff

    SENSOR["📡 Harogic SAN-400 (9kHz - 40GHz)"]:::hardware

    subgraph LAYER1["🛡️ CAPA 1 — Interfaz de Hardware Tolerante a Fallos"]
        direction TB
        USB(("🔌 USB 3.0")):::hardware
        KERNEL["⚙️ Kernel USB Driver"]:::host

        subgraph WATCHDOG["Sistema Watchdog (Demonio en Espacio de Usuario)"]
            direction LR
            WD_LISTEN["watchdog_usb.sh"]:::bash
            WD_UDEV["99-harogic-docker.rules"]:::bash
            WD_RESTART["Bucle de Auto-Recuperación"]:::bash
            WD_LISTEN -->|"poll lsusb"| WD_UDEV
            WD_UDEV -->|"evento hotplug"| WD_RESTART
        end

        USB --> KERNEL
        KERNEL -.->|"Eventos del bus"| WATCHDOG
    end

    subgraph LAYER2["🐳 CAPA 2 — Adquisición Contenedorizada (RF-Swift)"]
        direction TB
        DOCKER{{"📦 Motor Docker"}}:::docker
        SOAPY["⚙️ SoapySDR (C++ / factory harogic)"]:::docker
        PYLIBS["🐍 Python3 + NumPy + SciPy"]:::python

        subgraph ACQUISITION["Pipeline de Adquisición"]
            direction LR
            PROBE["probe_device.py"]:::python
            CAPTURE["capture_iq.py"]:::python
            REPLAY["replay_iq.py"]:::python
            VALIDATE["validate_meta.py"]:::python
        end

        DOCKER -->|"Inyección HW"| SOAPY
        SOAPY -->|"Flujo IQ"| PYLIBS
        PYLIBS --> ACQUISITION
    end

    subgraph LAYER3["📊 CAPA 3 — Procesamiento de Señal y Extracción de Características"]
        direction TB

        subgraph DSP["Motor DSP"]
            direction LR
            STREAM["stream_processor.py"]:::python
            SPECTRO["generate_spectrogram.py"]:::python
            FEATURES["extract_features.py"]:::python
            STREAM -->|"Ring Buffer Lock-free"| SPECTRO
            SPECTRO -->|"Matriz Espectrograma (.npz)"| FEATURES
        end

        subgraph DSP_CONFIG["Configuración DSP (JSON)"]
            direction LR
            SPEC_CFG["spectrogram_config.json"]:::config
            FEAT_CFG["features_config_*.json"]:::config
        end

        DSP_CONFIG -.->|"Parámetros"| DSP
    end

    subgraph LAYER4["🚨 CAPA 4 — Motor de Eventos Tácticos (FSM)"]
        direction TB

        subgraph ENGINE["Motor de Eventos"]
            direction LR
            FSM["engine.py (FSM 4 Estados)"]:::alert
            RUNNER["run_event_engine.py"]:::python
            RUNNER -->|"Tramas CSV"| FSM
        end

        subgraph RULES["Reglas y Perfiles (JSON)"]
            direction LR
            RULES_CFG["rules_config.json"]:::config
            PROFILES["continuous | packet_traffic"]:::config
        end

        RULES -.->|"Políticas"| ENGINE
    end

    subgraph PERSISTENCE["💾 Capa de Persistencia"]
        direction LR
        RAW[("📁 .iq / .sigmf-meta")]:::storage
        NPZ[("📊 Espectrograma (.npz)")]:::storage
        CSV[("📄 Características (.csv)")]:::storage
        EVENTS[("🚨 Eventos (.json)")]:::storage
    end

    SENSOR <-->|"USB 3.0"| LAYER1
    WD_RESTART -.->|"docker restart"| DOCKER
    KERNEL <-->|"Bind Mount (/dev/bus/usb)"| DOCKER
    ACQUISITION ==>|"Bloques temporales"| RAW
    RAW -.->|"Replay / Offline"| DSP
    DSP ==>|"Métricas Matemáticas"| CSV
    SPECTRO ==>|"Matriz FFT"| NPZ
    CSV -.->|"Evaluación de reglas"| ENGINE
    FSM ==>|"Alertas Filtradas"| EVENTS
```

### Resumen Capa por Capa

| Capa | Propósito | Componentes Clave | Día |
|:---:|:---|:---|:---:|
| **1** | **Hardware Tolerante a Fallos** — Inmuniza la captura contra desconexiones USB y fallos eléctricos. | `watchdog_usb.sh`, `99-harogic-docker.rules`, `capture.sh` | 5-7 |
| **2** | **Adquisición Contenedorizada** — Captura datos IQ crudos dentro de Docker con contratos de metadatos SigMF y hashes SHA256 de integridad. | `capture_iq.py`, `validate_meta.py`, `probe_device.py` | 1-8 |
| **3** | **DSP y Extracción de Características** — Genera espectrogramas (FFT) y extrae métricas físicas (SNR, potencia, ancho de banda) por trama. | `stream_processor.py`, `extract_features.py`, `features_config_*.json` | 9-13 |
| **4** | **Motor de Eventos Tácticos** — Una FSM determinista que convierte métricas crudas en alertas consolidadas con severidad, confianza y lógica anti-fragmentación. | `engine.py`, `run_event_engine.py`, `rules_config.json` | 14 |

---

## 🛡️ Watchdog y Tolerancia a Fallos (Detalle)

Uno de los subsistemas más críticos es el **Watchdog en Espacio de Usuario**, que opera fuera del contenedor Docker para garantizar resiliencia de hardware:

```
┌──────────────────────────────────────────────────┐
│                HOST OS (Bare Metal)               │
│                                                   │
│   ┌───────────────┐     ┌──────────────────────┐  │
│   │ watchdog_usb.sh│────▶│ 99-harogic-docker    │  │
│   │ (Bucle Demonio)│     │ .rules (udev)        │  │
│   └───────┬───────┘     └──────────────────────┘  │
│           │                                        │
│           │  ¿Desconexión USB detectada?            │
│           │  SÍ ──▶ docker restart harogic_final   │
│           │  ──▶ capture.sh relanza el pipeline    │
│           │                                        │
│   ┌───────▼────────────────────────────────────┐   │
│   │         Contenedor Docker (RF-Swift)        │   │
│   │   SoapySDR ──▶ capture_iq.py ──▶ .iq files │   │
│   └─────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────┘
```

**¿Por qué importa?** En despliegues de campo, los cables USB se desconectan, el voltaje fluctúa y los sensores se sobrecalientan. Sin el Watchdog, cualquier desconexión mata la sesión de captura entera. Con él, el sistema **se auto-repara** en segundos y retoma la captura del tiempo restante — sin intervención humana.

---

## ⚙️ Requisitos de Hardware

| Componente | Especificación | Rol |
| :--- | :--- | :--- |
| **Analizador SDR** | Harogic SAN-400 (9 kHz – 40 GHz) | Escaneo principal de espectro electromagnético. |
| **Interfaz** | USB 3.0 / USB-C de Alta Velocidad | Transferencia de muestras IQ en tiempo real. |
| **Host** | Ubuntu Linux (Físico o VM) | Contenedores, almacenamiento y Watchdog. |

---

## 📥 Dependencias Externas y Descargas

Este repositorio **no** contiene binarios de terceros ni software pesado del fabricante.

1. **Contenedor RF-Swift (PentHertz):**
   - **Pull:** `docker pull penthertz/rfswift_noble:sdr_full`
   - **Documentación:** [PentHertz GitHub / RF-Swift](https://github.com/PentHertz/RF-Swift)
2. **SAStudio4 y SDK de Harogic:**
   - **Descarga:** [Página Oficial de Descargas de Harogic](http://www.harogic.eu/download/)
   - *Nota: Solo necesario si deseas usar la interfaz gráfica original. Spectre-Horizon usa el driver SoapySDR embebido dentro del contenedor RF-Swift.*

---

## 🚀 Instalación y Despliegue

### 1. Preparar el Entorno
```bash
rfswift run -i penthertz/rfswift_noble:sdr_full -s /dev/bus/usb -u 1
```

### 2. Clonar el Repositorio
```bash
git clone https://github.com/dielectronico314/Spectre-Horizon.git
cd Spectre-Horizon
```

---

## 🛠 Uso y Comandos

### Captura Resiliente
```bash
./scripts/capture.sh --freq 106.5e6 --rate 1.953125e6 --gain 0 --duration 180 --chunk-duration 30
```

### Extracción de Características (DSP)
```bash
python3 scripts/extract_features.py captura.npz --config config/features_config_fm_106.5.json --out-dir results/
```

### Motor de Eventos (Alertas Tácticas)
```bash
python3 scripts/run_event_engine.py results/features_captura.csv --rules-config config/rules_config.json --out-dir results/
```

---

## 📦 Estructura de Datos (SigMF)

Por cada bloque de captura se generan dos archivos acoplados:

1. **Archivo Binario (.iq):** Volcado crudo de memoria con flotantes complejos (`CF32` o `CI16`).
2. **Archivo de Metadatos (.sigmf-meta):** JSON universal con telemetría de hardware, hashes SHA256 de custodia de datos y parámetros de señal.

Para la especificación completa del esquema SigMF v0.1, consulta `docs/CONTRATO_METADATA.md`.

---

## 🗂 Estructura del Proyecto

```
Spectre-Horizon/
├── app/
│   ├── events/
│   │   └── engine.py              # FSM: motor de eventos tácticos (4 estados)
│   └── processing/
│       └── features.py            # Matemáticas DSP (potencia, SNR, picos)
├── config/
│   ├── features_config_*.json     # Parámetros de extracción por banda
│   ├── rules_config.json          # Políticas de decisión del motor de eventos
│   └── spectrogram_config.json    # Parámetros FFT/espectrograma
├── scripts/
│   ├── capture_iq.py              # Pipeline principal de adquisición IQ
│   ├── stream_processor.py        # Procesador FFT streaming en tiempo real
│   ├── extract_features.py        # CLI de extracción de características DSP
│   ├── run_event_engine.py        # CLI del motor de eventos
│   ├── validate_meta.py           # Auditor de metadatos SigMF
│   ├── probe_device.py            # Detección de hardware (salida JSON)
│   ├── watchdog_usb.sh            # Demonio de hotplug USB
│   └── capture.sh                 # Wrapper de captura resiliente
├── tests/
│   ├── test_events_known.py       # Tests oráculo del motor de eventos (A-F)
│   ├── test_features_known.py     # Tests de regresión de extracción DSP
│   └── golden/                    # Salidas esperadas deterministas
├── docs/
│   ├── TABLERO_20_DIAS.md         # Tablero de progreso de 20 días
│   ├── EVENTS_REF.md              # Manual de referencia del motor de eventos
│   ├── FEATURES_REF.md            # Referencia de extracción de características
│   ├── ESPECTROGRAMA_REF.md       # Referencia del algoritmo de espectrograma
│   ├── CONTRATO_METADATA.md       # Especificación del esquema SigMF v0.1
│   └── BACKLOG.md                 # Deuda técnica y trabajo futuro
└── README.md
```

---

## 🗓 Roadmap (Plan de 20 Días)

Actualmente en **Fase 3** (Eventos e Inteligencia). Progreso:

- [x] **Día 1-3:** Baseline de Hardware y Entorno Contenedorizado (RF-Swift).
- [x] **Día 4:** Detección Programática de Hardware con JSON API.
- [x] **Día 5:** Bucle Robusto en CF32 para Capturas Ininterrumpidas.
- [x] **Día 6:** Pruebas de Estrés y Telemetría de Hardware (PSUtil).
- [x] **Día 7:** Arquitectura Inmune (Reconexión Hotplug, USB Watchdog y Chunking).
- [x] **Día 8:** Contrato Oficial de Metadata (SigMF v0.1) y Validador SHA256.
- [x] **Día 9:** Replay Offline Determinista de Capturas IQ.
- [x] **Día 10:** Prueba de Aceptación de Adquisición de 60 Minutos.
- [x] **Día 11:** Generación Offline de Espectrograma (Algoritmo FFT de Referencia).
- [x] **Día 12:** Pipeline de Streaming FFT en Tiempo Real (Ring Buffer Lock-free).
- [x] **Día 13:** Extracción de Características DSP (Potencia, SNR, Ancho de Banda por trama).
- [x] **Día 14:** Motor de Eventos Lógico Determinista (FSM para alertas tácticas).
- [ ] **Día 15:** Empaquetado de Evidencia con hashes de integridad.
- [ ] **Día 16:** API REST para consulta de sesiones y eventos (FastAPI).
- [ ] **Día 17:** Dashboard Web Mínimo (Waterfall + Tabla de Alertas).
- [ ] **Día 18:** Generación Automatizada de Reportes de Sesión (HTML/PDF).
- [ ] **Día 19:** Empaquetado del Sistema y Ensayo General.
- [ ] **Día 20:** Aceptación Formal, Demo en Vivo e Informe Final.

---
*Diseñado con el máximo rigor para investigación RF.*
