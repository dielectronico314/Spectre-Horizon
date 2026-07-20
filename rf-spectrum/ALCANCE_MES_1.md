# ALCANCE_MES_1.md — MVP Conciencia de Espectro Familia A

**Periodo:** 15 de julio al 11 de agosto de 2026  
**Equipo:** 1 Desarrollador (Cenital Space)  
**Versión:** 1.0  
**Estado:** Firmado / Vigente  

---

## 1. Propósito Comercial del MVP
El objetivo de este primer mes es construir un hilo vertical funcional extremo a extremo para **demostrar la viabilidad del hardware Harogic y capturar el valor de Conciencia de Espectro**. No se busca construir una plataforma comercial terminada, sino proveer evidencia técnica reproducible de que el sensor se puede controlar, capturar, procesar y visualizar de forma estable y robusta.

---

## 2. Alcance Incluido (In-Scope)
El desarrollo del mes 1 se limitará exclusivamente a las siguientes capacidades:

### 1. Adquisición y Diagnóstico de Hardware
* **Detección Programática:** Comando que identifica si el sensor Harogic está conectado, si tiene los drivers correctos y si el CalFile es válido.
* **Captura Estable:** Adquisición de señales IQ con configuración parametrizable (frecuencia, sample rate, ganancia, duración).
* **Robustez y Observabilidad:** Monitoreo en tiempo real de tasa de datos (throughput), pérdida de muestras (overflows) y errores de hardware.
* **Tolerancia a Fallos:** Grabación en archivos por bloques cortos de tiempo y reconexión automática ante interrupciones físicas del sensor sin perder bloques previamente escritos.

### 2. Procesamiento Reproducible
* **Contrato de Grabación:** Metadata v0.1 validada (formato compatible con SigMF) que incluye toda la configuración física del sensor.
* **Replay Determinista:** Un lector de sesiones grabadas que simula la adquisición en vivo, permitiendo pruebas y desarrollo sin necesidad de tener el hardware físicamente conectado.
* **Procesamiento de Espectrograma:** Transformación continua de IQ a representación espectral (FFT, ventana, escala logarítmica) tanto en vivo como en replay.
* **Extracción de Features:** Cálculo y exportación de características básicas (potencia RMS, pico de frecuencia central, SNR estimada, ancho de banda aproximado).

### 3. Motor de Eventos y Evidencia
* **Motor de Reglas Simple:** Generación de alertas basadas en reglas fijas (ej. potencia sobre umbral en bandas de interés).
* **Paquete de Evidencia Trazable:** Generación automática de una carpeta o archivo por evento que incluye metadata, versión de software, hashes de validación, espectrograma e IQ selectivo de respaldo.

### 4. Interfaz y Reporte (Dashboard Local)
* **API de Integración:** Endpoints construidos en FastAPI para consultar salud del sensor, listado de sesiones, alertas y descarga de evidencia.
* **Dashboard Mínimo:** Vista web sencilla (HTML servido directamente por FastAPI) para visualizar estado del sensor, cascada de espectrograma (waterfall) básica, tabla de eventos detectados y detalle de evidencia.
* **Reporte Técnico Automático:** Generación automática de un reporte técnico de la sesión (HTML/PDF) con métricas, eventos encontrados y trazabilidad total.

---

## 3. Alcance Excluido (Out-of-Scope)
Para mantener la viabilidad de la entrega por una sola persona en 4 semanas, los siguientes elementos **quedan estrictamente fuera** de esta fase:

* 🚫 **Clasificación por Inteligencia Artificial / TensorRT:** No habrá red neuronal para reconocimiento automático de señales o drones en este hito.
* 🚫 **Biblioteca de Drones / Catálogo de Firmas:** No se construirá un diccionario de dispositivos.
* 🚫 **Geolocalización / TDOA / Radar:** Excluidas capacidades de triangulación geográfica y procesamiento de múltiples sensores remotos simultáneos.
* 🚫 **Plataforma SaaS Multi-inquilino / Gestión de Usuarios:** Sin login, roles de usuario, ni sincronización en la nube.
* 🚫 **Base de Datos Pesada (PostgreSQL, InfluxDB):** Toda la metadata e historial se almacenará de manera ligera utilizando **SQLite** local.
* 🚫 **Frontend Moderno Separado (React, Vue, Angular):** No se mantendrá un frontend desacoplado para evitar el consumo de tiempo en configuración de compilación, empaquetado o APIs adicionales.

---

## 4. Criterios de Éxito de la Demostración (Día 20)
Al final del ciclo, se ejecutará una prueba formal donde el sistema debe:
1. Demostrar **60 minutos continuos de operación estable**.
2. Funcionar de extremo a extremo en **modo Replay** y en **modo Vivo** de forma idéntica.
3. Recuperarse con éxito de una desconexión simulada del sensor sin detener el sistema.
4. Exportar un reporte de aceptación con un paquete de evidencia firmado.
