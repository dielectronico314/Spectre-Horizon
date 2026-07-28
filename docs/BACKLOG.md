# Backlog de Mejoras y Deuda Técnica

Este documento recopila decisiones arquitectónicas, mejoras lógicas y optimizaciones que se han pospuesto para iteraciones futuras del proyecto Spectre-Horizon.

---

## 1. Lógica de Reanudación de Tiempo en el Watchdog (Capa de Adquisición)

**Contexto actual:**
Actualmente (v0.1), el script `capture.sh` funciona como un Watchdog sin estado (*stateless*). Si se le solicita capturar datos durante 60 minutos (3600 segundos) y ocurre una interrupción física del hardware (ej. caída de voltaje, desconexión USB) en el minuto 31, el Watchdog reiniciará el hardware pero lanzará una **nueva sesión de 60 minutos desde cero**.

**El Problema Lógico:**
Si el operador programó una ventana estricta de grabación (ej. "grabar solo por la próxima hora"), el comportamiento de reiniciar el contador temporal extiende la grabación más allá del marco de tiempo deseado (en el ejemplo, se grabarían 31 min + 60 min = 91 minutos totales).

**Solución Propuesta para el Futuro:**
Modificar el script Bash (`capture.sh`) para que inyecte "consciencia de tiempo" (Time Awareness). 
1. Al iniciar, el script debe guardar el `TIMESTAMP_INICIO`.
2. Dentro del bucle `while true`, antes de relanzar `capture_iq.py`, debe calcular:
   `TIEMPO_TRANSCURRIDO = AHORA - TIMESTAMP_INICIO`
   `TIEMPO_RESTANTE = DURACION_TOTAL_OBJETIVO - TIEMPO_TRANSCURRIDO`
3. Si el error ocurre en el minuto 31, el Watchdog le ordenará a Python: "Captura, pero tu nuevo `--duration` es de 29 minutos".
4. Si `TIEMPO_RESTANTE <= 0`, el script debe terminar (exit 0) de manera natural sin intentar reiniciar el hardware.

**Impacto:** 
Bajo, no bloquea el desarrollo actual de algoritmos espectrales (Días 11 en adelante), pero es altamente recomendado implementarlo antes de desplegar sensores de forma autónoma en misiones de tiempo crítico.
