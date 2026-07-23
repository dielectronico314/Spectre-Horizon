# Inventario Técnico del Proyecto — MVP Conciencia de Espectro

Este archivo contiene el registro detallado del hardware y software utilizado para la ejecución y demostración del MVP de Conciencia de Espectro.
---

## 1. Hardware y Sensores

### 1.1. Receptor de Espectro (SDR)
* **Marca/Proveedor:** Harogic Technologies
* **Modelo Exacto:** Harogic 400

* **Versión de Firmware:** FX3: 0.55.8 / MFW: 0.55.65 / FFW: 0.55.28
* **CalFile (Archivo de Calibración):** Integrado en memoria interna del dispositivo (cargado automáticamente por SAStudio4)

### 1.2. Antenas y Cableado
* **Antena Principal:** Antena dipolo telescópica (tipo "orejas de conejo" de dos elementos)
* **Tipo de Conector/Cable:** Conexión directa SMA
* **Atenuadores / Filtros:** N/A (conexión directa para prueba)

### 1.3. Computador de Desarrollo / Despliegue (Host)
* **Dispositivo Dedicado:** PC de Escritorio Local
* **Procesador (CPU):** Intel(R) Core(TM) Ultra 7 265KF
* **Memoria RAM:** 64GB
* **Almacenamiento:** SSD NVMe 1.5TB

---

## 2. Software y Entorno de Ejecución

### 2.1. Sistema Operativo
* **Distribución/Versión:** Ubuntu 22.04.5 LTS
* **Kernel:** 6.8.0-124-generic

### 2.2. Drivers y Acceso a Hardware
* **SDK Harogic (HTRA SDK):** Nativo (incluido con SAStudio)
* **Capa de Abstracción SDR:** N/A
* **Módulo de Driver SDR:** Driver nativo USB Harogic
* **Herramienta Comercial de Prueba:** SAStudio4 v4.3.55.30 (utilizada para pruebas de cordura iniciales)

---

## 3. Contactos y Soporte Técnico
* **Proveedor del Hardware:** `[Nombre del contacto de soporte del proveedor Harogic / PentHertz]`
* **Correo de Soporte:** `[Email de soporte del proveedor]`
* **Responsable Técnico Cenital Space:** `Diego`
