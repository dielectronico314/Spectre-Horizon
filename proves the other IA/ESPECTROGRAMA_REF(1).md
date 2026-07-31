# Espectrograma offline — Referencia (Día 11)

Entregable: `scripts/generate_spectrogram.py` + `config/spectrogram_config.json`.
Entrada: `.sigmf-meta` + `.sigmf-data`/`.iq`. Salida: PNG, `.npz` (float32) y `manifest.json`.

```bash
python3 scripts/generate_spectrogram.py capturas/cap_001.sigmf-meta \
    -c config/spectrogram_config.json -o out/
```

---

## 1. Escala: la única decisión que importa

Se normaliza por la **ganancia coherente** de la ventana, `S1 = Σw[n]`:

$$P[k] = \frac{\left|\mathrm{FFT}(x\cdot w)[k]\right|^2}{S_1^2}, \qquad \mathrm{dBFS} = 10\log_{10}P[k]$$

donde `x` ya viene dividido por el fondo de escala del ADC (`ci16_le` → `/32768`,
derivado de `core:datatype`, no hardcodeado).

Con esta normalización:

| | lee |
|---|---|
| Tono CW complejo a fondo de escala, centrado en bin | **0.0 dBFS** |
| Piso de ruido | **dBFS por RBW** |
| Densidad espectral | `dBFS − 10·log₁₀(RBW)` |

**Verificado numéricamente:**
- Tono CW sintético a fondo de escala → `−0.0009 dBFS` (el residuo es el redondeo a int16).
- Ruido blanco de potencia total −60 dBFS, NFFT=1024, Hann → medida `−88.354`, teoría `−88.342` dBFS/RBW. Error 0.012 dB.

### Por qué no hay una normalización única

No existe un escalado correcto simultáneamente para tono y para ruido:

- **`/S1²`** (ganancia coherente) → el tono lee su potencia real; el ruido lee potencia por RBW.
- **`/(fs·S2)`** (densidad, `S2 = Σw²`) → el ruido lee W/Hz; el tono lee mal por un factor que depende de la ventana.

Se eligió la primera: es la convención de analizador de espectro. Se aplica una sola vez, está declarada en el manifest y **nunca se mezcla** con la otra. Si `scipy.signal.spectrogram` se usara en lugar del motor propio, el equivalente exacto es `scaling='spectrum'`, no `'density'` (el default).

**El nivel del piso de ruido no significa nada sin declarar el RBW.** Por eso RBW aparece en el título del PNG, en la etiqueta del colorbar y en el manifest.

### Rango dinámico de las muestras de 16 bits

El límite real **no** es el SNR de cuantización del ADC (≈ 6.02·16 + 1.76 ≈ 98 dB para real; para IQ complejo el ruido de cuantización total es ≈ −96 dBFS). La FFT reparte ese ruido entre los bins y **gana rango dinámico por proceso**:

$$\text{ganancia de proceso} = 10\log_{10}\frac{N_{FFT}}{\mathrm{ENBW}_{bins}}$$

Con NFFT=1024 y Hann (ENBW = 1.5 bins) → **28.3 dB**. El piso visible de cuantización queda cerca de −124 dBFS/RBW, muy por debajo del piso de ruido térmico del front-end. Conclusión práctica: **el piso lo fija el ruido del receptor y el reference level, no los 16 bits.** Subir NFFT baja el piso visible 3 dB por duplicación, sin ganar SNR real.

### dBFS ≠ dBm

La salida es honestamente **relativa a fondo de escala**. El paso a dBm es un offset constante que requiere el reference level del Harogic y el factor de escala a volts del paquete. Cuando ese dato se registre en el metadato, se suma vía `calibration.cal_offset_db` sin recalcular nada. Mientras sea `0.0`, no se afirma potencia absoluta.

---

## 2. Los parámetros del motor se derivan, no se eligen

$$\Delta f = \frac{f_s}{N_{FFT}} \quad\big|\quad \mathrm{RBW} = \mathrm{ENBW}_{bins}\cdot\Delta f \quad\big|\quad \Delta t = \frac{N_{FFT}}{f_s} \quad\big|\quad \mathrm{hop} = N_{FFT}(1-\text{overlap})$$

**NFFT se despeja del RBW objetivo:** `NFFT = ENBW_bins · fs / RBW_objetivo`. `1024` no es un balance, es un default heredado. A 128 MSa/s da RBW ≈ 187 kHz — inútil para un canal de 12.5 kHz. Baja `fs` por decimación en el equipo o sube NFFT. Offline el costo es irrelevante: si dudas, genera dos resoluciones (256 para tiempo, 8192 para frecuencia) y compara.

### Ventana: se elige por tarea

| Ventana | ENBW (bins) | 1.er lóbulo lateral | Scalloping | Usar para |
|---|---|---|---|---|
| `boxcar` | 1.00 | −13 dB | 3.92 dB | pulsos aislados, máxima resolución temporal |
| `hann` | 1.50 | −31 dB | 1.42 dB | PSD genérica |
| `hamming` | 1.36 | −43 dB | 1.78 dB | compromiso |
| `blackmanharris` | 2.00 | −92 dB | 0.83 dB | señal débil junto a una fuerte |
| `flattop` | 3.77 | −93 dB | <0.05 dB | medir amplitud de CW de frecuencia desconocida |

Hann arrastra 1.42 dB de *scalloping loss*: si el tono cae entre bins, **lo mides bajo por hasta 1.42 dB**. Para medición de amplitud eso es un error, no un detalle. Y con −31 dB de lóbulo lateral, una portadora fuerte tapa cualquier vecina débil.

Se usa `scipy.signal.get_window(..., fftbins=True)` → ventana **periódica**. `np.hanning` es simétrica y mete un sesgo de fuga leve pero real en análisis espectral.

### Overlap 50% no protege transitorios

Con Hann, 50% cumple COLA y da casi toda la reducción de varianza útil; pasar de 75% es CPU tirado. Pero **un pulso en el borde de la trama lo atenúa el taper varios dB**, sin importar el overlap.

Si el objetivo es detectar pulsos cortos, el camino correcto no es subir el overlap: es un **detector de potencia a tasa completa** (`|I|²+|Q|²`, sin FFT, vectorizable, casi gratis) que marca el instante del evento, y aplicar FFT solo en la vecindad. Es ~10× más barato y no depende de dónde cae el pulso.

---

## 3. Trampa de renderizado (esto sí rompe el entregable)

Un `.iq` de 1 s a 128 MSa/s con hop 512 produce **250 000 tramas**. Un PNG mide ~1600 px de ancho. `imshow`/`pcolormesh` submuestrean por vecino más cercano y **descartan el 99.4 % de las tramas** — incluidos los transitorios que el overlap del 50 % pagó.

La solución es reducción explícita **max-hold** al grid de pixeles (`png_time_reduction: "maxhold"`), que conserva el pico de cada grupo. `"mean"` solo para estimar piso de ruido. Sin esto, el espectrograma miente por omisión.

Relacionado: la matriz completa de ese ejemplo son **1 GB en float32**. Usa `fft.max_seconds` para acotar, o guarda solo el rango de interés. `savez_compressed` sobre float32 casi no comprime y cuesta tiempo: se usa `savez` plano.

---

## 4. Reproducibilidad: verificable, no asumida

> ⚠️ **"Misma entrada + mismo JSON → salida idéntica bit a bit" es falso** como afirmación general.

La FFT en punto flotante **no** es bit-exacta entre versiones de NumPy/pocketfft/FFTW, entre anchos de SIMD, con o sin FMA, ni entre arquitecturas de CPU: el orden de suma cambia. Prometer bit-exactitud sin fijar el entorno es una afirmación que no se sostiene en una auditoría.

Lo que sí se garantiza y se implementa:

1. `sha256` del `.iq`, del config, del `.npz` y del PNG → en `manifest.json`.
2. Versiones de Python/NumPy/SciPy/matplotlib + arquitectura registradas en cada corrida.
3. Parámetros **resueltos** (no solo el archivo de config) serializados, para detectar defaults implícitos.
4. PNG sin timestamp: `savefig(metadata={"Software": None, "Creation Time": None})`. Sin esto el PNG cambia de hash en cada corrida aunque los datos sean idénticos.

**Verificado:** dos corridas consecutivas en el mismo contenedor → PNG bit-idéntico.

Para que la afirmación fuerte sea válida hay que fijar el **digest** de la imagen del contenedor (no el tag) y la arquitectura del host. Con eso, bit-exacto; sin eso, "reproducible dentro de tolerancia numérica" y los hashes te dicen cuándo algo cambió.

---

## 5. Imagen de referencia

`out/cap_demo_espectrograma.png` — captura sintética de validación (fs = 2 MSa/s, fc = 100 MHz, `ci16_le`):

- Tono CW a fondo de escala en 100.25 MHz (bin exacto) → lee 0.00 dBFS. **Valida la normalización.**
- Piso de ruido a −60 dBFS totales → −88.3 dBFS/RBW. **Valida la ganancia de proceso.**
- Pulso de 100 µs en −300 kHz. **Valida que el max-hold lo preserve.**

Este archivo debe regenerarse y compararse por hash cada vez que se toque el motor: es el test de regresión del pipeline.
