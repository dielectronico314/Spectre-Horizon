# Referencia de Extracción de Features (Día 13)

Este documento detalla las matemáticas, unidades y limitaciones de las características paramétricas extraídas por el sistema a partir de los espectrogramas (`.npz`). Todas las funciones se encuentran en `app/processing/features.py`.

## 1. Pico y Frecuencia Central (`pico_dbfs`, `freq_pico_hz`)
- **Unidad:** dBFS (Potencia Pico), Hz (Frecuencia).
- **Cálculo:** Búsqueda del máximo valor absoluto en los bins de la banda de interés en una trama determinada.
- **Limitaciones:** Sujeto a *Scalloping Loss* (hasta 1.42 dB para ventana de Hann) si la frecuencia real no coincide exactamente con el centro del bin de la FFT.

## 2. Potencia de Banda / Channel Power (`potencia_dbfs` y `potencia_media_dbfs`)
- **Unidad:** dBFS.
- **Cálculo:** Para una trama individual (`potencia_dbfs`), se convierten todos los bins de la banda a potencia lineal ($10^{dB/10}$), se suman, y se divide la suma total por el Factor de Ancho de Banda de Ruido Equivalente (`ENBW_bins`) de la ventana temporal utilizada (ej. 1.5 para Hann). Finalmente se convierte nuevamente a dBFS.
- **Aclaración Importante (Resumen de sesión):** La métrica `potencia_media_dbfs` en el JSON final promedia la potencia de banda a lo largo de **TODA la sesión** (incluyendo los momentos de silencio). No representa la potencia exclusiva de la señal mientras está activa (Burst).
- **Limitaciones:** Esta métrica asume que la señal ocupa múltiples bins. No debe confundirse con la potencia del "pico".

## 3. Ancho de Banda Ocupado / OBW (`bw_hz`)
- **Unidad:** Hz.
- **Cálculo:** Basado en el método de porcentaje de potencia (por defecto 99%). Se calcula la potencia acumulada (`cumsum`) lineal a través de la banda, marcando las frecuencias donde se cruzan los umbrales de $0.5\%$ y $99.5\%$.
- **Limitaciones:** Asume **un único lóbulo dominante** de energía en la banda. Si existen emisiones múltiples y separadas dentro de la misma banda configurada, el ancho de banda reportado abarcará desde la primera hasta la última sin reflejar la separación.

## 4. Estimación de Piso de Ruido y SNR (`snr_db`)
- **Unidad:** dB (Relación).
- **Cálculo:** $SNR = Potencia\_Banda - Piso\_Ruido$.
- **Estrategias de Piso de Ruido:**
  - `spectral`: Toma la mediana de potencia de bins fuera de la banda (usando guard bins) en la misma trama. Ideal para señales continuas que nunca se apagan (Ej. Radio FM).
  - `temporal`: Toma la mediana de potencia de la propia banda en tramas históricas de "silencio" (cuando no hay señal). Ideal para ráfagas (bursts) donde el ruido en la banda puede medirse entre transmisiones.

## 5. Duración y Presencia (`presente`, `duracion_s`)
- **Unidad:** Booleano, Segundos.
- **Cálculo:** Lógica de estado con **histéresis**. 
  - Para considerar un encendido, el SNR debe superar el `margin_on_db` durante al menos `N` tramas consecutivas.
  - Para un apagado, el SNR debe caer por debajo de `margin_off_db` durante al menos `N` tramas consecutivas.
- **Limitaciones:** Es un contador simple de presencia y duración acumulada. **No es un motor de eventos**; no maneja identidades de eventos, rangos de severidad, ni emite alertas en vivo (Eso es dominio del motor de eventos del Día 14).
