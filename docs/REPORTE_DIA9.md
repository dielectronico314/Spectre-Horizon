# Reporte de Cierre: Día 9 - Replay Offline Determinista

**Fecha de Ejecución:** Día 9 del Roadmap (Semana 3)
**Objetivo Principal:** Bipartición de la arquitectura para permitir procesamiento agnóstico mediante un motor de reproducción offline.
**Estado:** ✅ **COMPLETADO**

---

## 🎯 Hitos Alcanzados

Durante esta jornada logramos aislar exitosamente el sistema de procesamiento (aguas abajo) de la fuente de captura de hardware (SDR Harogic). Esto se logró construyendo un simulador de transmisión en vivo basado en archivos grabados.

### 1. Motor de Reproducción Criptográfica (`replay_iq.py`)
Se desarrolló el componente central del Día 9. Sus características clave incluyen:
* **Agnosticismo de Hardware:** Trata el archivo binario (`.iq`) y lo inyecta a la tubería de análisis de datos de forma que los futuros algoritmos no sean capaces de distinguir si la data proviene de una antena física o de un almacenamiento en disco.
* **Emulación de Tiempo Real Estricta:** Utiliza la variable `core:sample_rate` del metadato SigMF para retrasar de forma inteligente el procesamiento, garantizando que un archivo que duró 10 segundos en grabarse, durará exactamente 10 segundos en reproducirse. Esto evita desbordamientos (*overflows*) en el análisis de memoria.
* **Cadena de Custodia (Auditoría SHA256):** Antes de inyectar el primer byte, el script calcula el Hash del archivo completo y lo cruza obligatoriamente con el Hash declarado en el contrato `.sigmf-meta`. Toda alteración detiene el flujo inmediatamente, blindando la evidencia militar/forense.

### 2. Wrapper Aislado (`replay.sh`)
Para mantener el estándar de que "nada contamina la máquina Host", el sistema de Replay se encapsuló en un script Bash que enruta los comandos y las validaciones de directorios directamente a las entrañas del contenedor Docker (`mysdr`), manteniendo la fluidez operativa del usuario.

### 3. Generador Sintético de RF (`generate_synthetic_iq.py`)
Como hito adicional para probar exhaustivamente el ecosistema, se programó un creador de *mock data*.
* Es capaz de fabricar señales electromagnéticas virtuales (por ejemplo, una portadora de 5GHz con ruido y tono) usando matemáticas puras (`Numpy`).
* Inyecta todas las variables exigidas por nuestro estricto Contrato SigMF v0.1 (`core:hw`, `core:overflows`, `core:author`, etc.).
* Alimenta con éxito al sistema de `validate.sh` y al `replay.sh`, probando de manera fehaciente que nuestro pipeline es 100% agnóstico.

---

## 🚀 Valor de Negocio (El porqué)
Con la entrega del Día 9, el equipo de desarrollo ya no depende de la disponibilidad física del hardware de Harogic. El equipo puede simular cientos de horas de vuelo de drones falsos, alimentarlos al sistema y desarrollar detectores de inteligencia artificial, FFTs y motores de alertas de forma completamente descentralizada. 

Además, si el día de mañana se reemplaza la marca del sensor (Harogic por Ettus, HackRF o BladeRF), todo el software desarrollado a partir del Día 10 seguirá funcionando intacto gracias a esta sólida bipartición arquitectónica.
