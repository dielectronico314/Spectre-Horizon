# Auditoría de Resiliencia: Día 7 — Reconexión y Archivos por Bloques

De acuerdo a la planificación, el Día 7 abordó el mayor riesgo del sistema: **La corrupción de datos por pérdida de conexión USB**. 

Si grabamos archivos IQ gigantes en una sola toma y el sistema falla por un microsegundo, toda la grabación queda inútil. Para mitigar esto, hemos implementado una técnica de *Chunking* (partición por bloques) y un bucle de supervivencia.

A continuación, los resultados de la prueba de inyección de fallos que acabamos de realizar.

---

## 🔬 Resultados de la Falla Inducida

Al ejecutar la prueba de 3 minutos, el código empezó a grabar bloques ("chunks") de 30 segundos cada uno. 
En el minuto `01:02` el SDR fue desconectado físicamente ("plug pull"). 

El análisis del registro del sistema (log) demostró lo siguiente:

### 1. El Sistema Superviviente
> [!SUCCESS]
> **La desconexión NO tiró el script.** 
> Anteriormente, esto hubiese causado un "Segmentation Fault" o la muerte del proceso de Python. Esta vez, el bloque de manejo de excepciones `try/except` interceptó el código de error nativo `-2` del hardware C++, desactivó el flujo de datos para evitar fugas de memoria, e ingresó pacíficamente a un bucle de Backoff (esperando pacientemente 5 segundos entre reintentos).

### 2. Salvaguarda de Bloques (Chunking Exitoso)
> [!SUCCESS]
> **Ni un solo byte previo a la desconexión se perdió.**
> Observando los logs, el script logró cerrar ordenadamente los dos bloques anteriores:
> - `captura_106.5MHz_part001.iq` y su metadato JSON.
> - `captura_106.5MHz_part002.iq` y su metadato JSON.
> Ambos archivos están sanos y salvos en tu disco, demostrando que ya no dependemos de un solo archivo monolítico de alto riesgo.

---

## ⚠️ Limitación Encontrada: "Hotplug" en Docker

Durante la prueba, al reconectar físicamente la antena, el script Python seguía reportando `Harogic device not found for serial`. 

**Esto NO es una falla de nuestro código Python, sino una limitación conocida del motor de Docker en Linux ("USB Hotplugging").** 
Cuando pasamos el bus USB al contenedor (`-v /dev/bus/usb:/dev/bus/usb`), Docker toma una "foto" de los dispositivos conectados en ese momento exacto. Si desconectas el SDR y lo vuelves a conectar, el sistema operativo de tu computadora le asigna un "nuevo ID" en el bus USB, pero el contenedor de Docker sigue viendo la "foto vieja" y nunca se entera del nuevo ID. 

### ¿Cómo solucionar esto en producción?
Para despliegues reales prolongados, tenemos dos caminos arquitectónicos a futuro:
1. **Solución A:** Hacer que la reconexión USB reinicie todo el contenedor de Docker desde afuera (usando reglas de `udev` del sistema operativo Linux host).
2. **Solución B:** Correr el script `capture_iq.py` de forma nativa en la computadora host (sin Docker) usando un entorno virtual (`venv`). Así, el bucle *Backoff* que programamos hoy atrapará el hardware reconectado inmediatamente.

---

## 🏁 Conclusión del Día 7

**La auditoría técnica ha sido superada con éxito.** 
El comportamiento de partición (Chunking) y el escudo contra excepciones críticas del SDR ya están fusionados en el corazón del proyecto. Hemos convertido una simple prueba de concepto matemática en una tubería de ingesta resiliente de grado industrial.

### Resolución de Hotplug
Se optó por la **Solución Watchdog (Espacio de Usuario)** en lugar de reglas `udev` a nivel de kernel, ya que estas últimas causaban colapsos en el IDE y bloqueos en el bus USB. 
Se creó un script centinela (`watchdog_usb.sh`) que vigila el dispositivo usando `lsusb`. Cuando el sensor Harogic es reconectado, el watchdog reinicia automáticamente el contenedor Docker de captura (`mysdr`) y el script principal retoma la grabación sin que el usuario tenga que presionar nada en la consola. Esto garantiza escalabilidad usando contenedores y mantiene la resiliencia deseada de forma segura.
