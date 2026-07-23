# Tablero de Control de 20 Días — MVP Conciencia de Espectro

Este tablero permite registrar el progreso diario durante las 4 semanas de ejecución del MVP (15 de julio al 11 de agosto de 2026). Cada día se cierra de manera explícita con su respectivo entregable y nivel de éxito.

---

## 📅 Semana 1 — Hardware, Entorno y Primera Captura

| Día | Fecha | Objetivo Ejecutivo | Entregable Clave | Estado |
|---|---|---|---|---|
| **Día 1** | Mié 15 Jul | Alcance, inventario y estructura de repositorio. | Repositorio inicial, `ALCANCE_MES_1.md`, `ADR 0001` y Tablero de Control. | **COMPLETADO** |
| **Día 2** | Jue 16 Jul | Prueba de cordura del hardware Harogic. | Archivo `BASELINE_HARDWARE.md` con parámetros de SAStudio4. | **COMPLETADO** |
| **Día 3** | Vie 17 Jul | Configuración de entorno reproducible de desarrollo. | `README.md` de instalación limpia y test unitario automatizado básico. | **COMPLETADO** |
| **Día 4** | Lun 20 Jul | Detección programática del sensor mediante Python. | Script `scripts/probe_device.py` con salidas JSON. | **COMPLETADO** |
| **Día 5** | Mar 21 Jul | Obtención de la primera captura binaria de IQ. | Archivo de captura IQ de 60s con metadata v0.1 validada. | **COMPLETADO** |

---

## 📅 Semana 2 — Adquisición Observable y Robusta

| Día | Fecha | Objetivo Ejecutivo | Entregable Clave | Estado |
|---|---|---|---|---|
| **Día 6** | Mié 22 Jul | Captura prolongada y métricas de observabilidad. | Reporte de estabilidad de 30 minutos (throughput/overflows). | *Pendiente* |
| **Día 7** | Jue 23 Jul | Control de pérdida de conexión y grabación segmentada. | Captura por bloques de tiempo con autorecuperación comprobada. | *Pendiente* |
| **Día 8** | Vie 24 Jul | Esquema definitivo de metadata y validación de hash. | Schema JSON de sesión compatible con SigMF y validador de integridad. | *Pendiente* |

---

## 📅 Semana 3 — Replay, Procesamiento y Eventos

| Día | Fecha | Objetivo Ejecutivo | Entregable Clave | Estado |
|---|---|---|---|---|
| **Día 9** | Lun 27 Jul | Replay offline determinista de capturas IQ. | Script de reproducción offline que emula flujo en vivo con hashes de seguridad. | *Pendiente* |
| **Día 10** | Mar 28 Jul | Ensayo y prueba de estabilidad de adquisición. | Archivo de aceptación `ACEPTACION_ADQUISICION_V01.md` de 60 min. | *Pendiente* |
| **Día 11** | Mié 29 Jul | Generación offline de espectrograma (Waterfall). | Algoritmo FFT/espectrograma de referencia reproducible. | *Pendiente* |
| **Día 12** | Jue 30 Jul | Pipeline de procesamiento espectral continuo (Streaming). | Procesamiento en tiempo real por bloques (Vivo y Replay). | *Pendiente* |
| **Día 13** | Vie 31 Jul | Extracción de features de espectro (Potencia, SNR, etc.). | Extractor de características espectrales y resumen JSON de sesión. | *Pendiente* |

---

## 📅 Semana 4 — Eventos, Evidencia y Visualización

| Día | Fecha | Objetivo Ejecutivo | Entregable Clave | Estado |
|---|---|---|---|---|
| **Día 14** | Lun 03 Ago | Motor de alertas espectrales por reglas fijas. | Motor de reglas capaz de levantar alertas bajo umbrales programados. | *Pendiente* |
| **Día 15** | Mar 04 Ago | Empaquetado y generación de paquetes de evidencia. | Estructura de evidencia por alerta con hashes de integridad. | *Pendiente* |
| **Día 16** | Mié 05 Ago | API REST para consulta de sesiones y eventos. | Endpoints en FastAPI documentados con Swagger interactivo. | *Pendiente* |
| **Día 17** | Jue 06 Ago | Dashboard de control web mínimo. | Pantalla de estado con Waterfall básico y tabla de alertas en vivo. | *Pendiente* |
| **Día 18** | Vie 07 Ago | Generación automatizada de reportes de sesión. | Reporte descargable (HTML imprimible o PDF) con historial espectral. | *Pendiente* |

---

## 📅 Cierre — Integración y Demostración Final

| Día | Fecha | Objetivo Ejecutivo | Entregable Clave | Estado |
|---|---|---|---|---|
| **Día 19** | Lun 10 Ago | Empaquetado del sistema y ensayo general. | Comando único de despliegue, guion de demo de 15 minutos y demo de 60s. | *Pendiente* |
| **Día 20** | Mar 11 Ago | Aceptación formal, demo en vivo e informe final. | Entrega de versión v0.1 y plan prioritario del Mes 2. | *Pendiente* |

---

### Instrucciones de Gobernanza Diaria
Cada día, al finalizar el trabajo:
1. Asegurar que el código esté integrado en la rama principal.
2. Comprobar que el entregable cumpla con el criterio de "Terminado cuando..." del plan principal.
3. Marcar el estado del día aquí como **COMPLETADO**.
4. Registrar observaciones críticas en una bitácora o notas operativas.
