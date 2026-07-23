# ADR 0001: Selección del Stack de Tecnología Inicial para el MVP

**Fecha:** 15 de julio de 2026  
**Estado:** Aceptado  
**Autor:** Cenital Space  

---

## 1. Contexto y Problema
Para construir un MVP funcional de Conciencia de Espectro en 4 semanas con un solo desarrollador, se necesita un conjunto de tecnologías que minimice los costos de integración, elimine cambios de contexto innecesarios y garantice una alta velocidad de iteración. 

El sistema tiene requerimientos de procesamiento de señales (DSP), control de hardware en tiempo real (adquisición IQ), persistencia de datos (metadata de sesiones) y una interfaz visual local (dashboard).

---

## 2. Decisiones de Arquitectura

Hemos tomado las siguientes decisiones técnicas estratégicas para el hito inicial:

### 2.1. Lenguaje Principal: Python 3
* **Decisión:** Usar Python 3 para todo el ciclo del backend, adquisición, DSP y utilidades.
* **Razón:** Es la "lingua franca" del procesamiento de señales de radiofrecuencia moderno y permite enlazar el backend (FastAPI) con las librerías matemáticas (NumPy, SciPy) y los bindings de hardware (SoapySDR/SoapyHarogic) sin cruzar fronteras de lenguaje.

### 2.2. Adquisición y Drivers: SoapyHarogic / HTRA SDK
* **Decisión:** Utilizar los bindings oficiales de `SoapyHarogic` (o herramientas del entorno PentHertz) y el SDK HTRA nativo para control de bajo nivel.
* **Razón:** SoapySDR provee una abstracción limpia para configuración de frecuencia, ganancias y muestreo, permitiendo además emular flujos fácilmente para el modo Replay offline.

### 2.3. Procesamiento Espectral (DSP): NumPy + SciPy
* **Decisión:** Usar Python acelerado mediante NumPy y SciPy para cálculos de FFT, ventanas y filtros.
* **Razón:** Evita depender de complejas cadenas de compilación en C++ o entornos gráficos pesados como GNU Radio en la base principal del código, facilitando las pruebas unitarias y la mantenibilidad.

### 2.4. Servidor API y Lógica de Negocio: FastAPI
* **Decisión:** Construir los endpoints utilizando FastAPI.
* **Razón:** Genera documentación automática de la API interactiva (Swagger), es asíncrono y de muy alto rendimiento, lo que facilita el streaming local de datos de control y eventos.

### 2.5. Base de Datos de Metadata: SQLite + SQLModel (or SQLAlchemy)
* **Decisión:** Usar SQLite para almacenar sesiones, eventos y configuraciones.
* **Razón:** Al ser una base de datos basada en un único archivo físico, no requiere instalación ni administración de un servicio (como PostgreSQL o InfluxDB), haciendo que la demo sea 100% portable y de arranque automático de un solo comando.

### 2.6. Almacenamiento de Señales IQ y Espectrogramas: Sistema de Archivos Local
* **Decisión:** Almacenar los archivos binarios de IQ (`.bin` o formato SigMF) y las imágenes del waterfall generadas directamente en el sistema de archivos del sistema operativo, ordenados bajo `/data/samples/`.
* **Razón:** Almacenar datos IQ masivos dentro de una base de datos degrada el rendimiento. El acceso a disco directo local es eficiente y simple para una demo de un solo nodo.

### 2.7. Interfaz de Usuario (UI): Plantillas HTML/JS Servidas por FastAPI
* **Decisión:** Usar plantillas HTML directas (Jinja2) y JavaScript simple (Vanilla JS o librerías ligeras como Chart.js para el espectrograma/gráficas) servidas directamente por el backend de FastAPI.
* **Razón:** Elimina la necesidad de usar entornos de frontend separados (como React o Vue) que requieren configuraciones complejas de node modules, empaquetadores (Vite/Webpack) y puertos separados, ahorrando días de desarrollo en coordinación de APIs.

---

## 3. Consecuencias

### 3.1. Consecuencias Positivas (Beneficios)
* **Altísima velocidad de desarrollo:** Un único desarrollador puede programar y depurar todo el flujo (desde la captura de bytes hasta la UI) en una sola sesión de editor.
* **Fácil despliegue:** La demo se puede correr clonando el repositorio y ejecutando un solo comando (ej. `python main.py` o similar).
* **Fácil Replay:** El backend puede cambiar de fuente (sensor real vs archivos locales) de forma transparente debido a la homogeneidad del stack.

### 3.2. Consecuencias Negativas (Límites / Deuda Técnica)
* **Escalabilidad horizontal limitada:** SQLite y el sistema de archivos local limitan el uso a un único equipo. Si en el futuro se requiere almacenamiento multi-sensor distribuido en la nube, se deberá migrar a PostgreSQL y almacenamiento de objetos S3.
* **UI Sencilla:** Al no usar React, la UI será extremadamente funcional pero no se beneficiará de complejos sistemas de componentes modernos de manera directa.
