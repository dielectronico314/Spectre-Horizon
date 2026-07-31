# Referencia del Motor de Eventos por Reglas (Día 14)

Este documento detalla la regla, la máquina de estados, las fórmulas de severidad/confianza,
y las limitaciones explícitas del motor de eventos. El código vive en `app/events/engine.py`
(máquina de estados pura, sin I/O) y `scripts/run_event_engine.py` (CLI: CSV → JSON).

Principio de capas heredado de días previos: **features mide, eventos decide**. El motor de
eventos no vuelve a tocar el espectrograma ni reestima el piso de ruido — consume directamente
el CSV por trama que produce `scripts/extract_features.py` (Día 13).

## 0. Lo que se hereda de Día 13 (no se reabre)

- Fuente de datos: `features_<sesion>.csv`, no el `.npz` crudo ni el streaming del Día 12.
- Deuda documentada, no bloqueante: el ~0.159% de desfase de `fs` (driver sin readback real)
  sigue siendo irrelevante a la escala de tiempo de eventos (segundos).
- El hueco de Día 13 (`potencia_media_dbfs` de sesión completa mezclaba silencio con señal) se
  resuelve aquí: `potencia_media_activa_dbfs` se calcula **solo** sobre las tramas que estuvieron
  genuinamente por encima del umbral durante el evento — ver sección 4.

## 1. La regla v0.1

Regla: potencia de banda sobre un umbral, dentro de una banda configurada.

```
activo(t) = potencia_banda_dB(t) >= umbral_on_dB
umbral_on_dB = piso_ruido_dB(banda) + margen_dB
```

### Espacio de decisión: SNR en vez de dBFS absoluto

`umbral_on_dB` depende de `piso_ruido_dB(banda)`, que en Día 13 ya se calculó por trama y por
banda (estrategia `spectral` o `temporal`, elegida por banda en `features_config*.json`) y quedó
guardado en la columna `snr_db` del CSV como `snr_db = potencia_dbfs - piso_ruido_dB`.

En vez de volver a leer/recalcular `piso_ruido_dB` dentro del motor de eventos (duplicando el
estimador que Día 13 ya resolvió), el motor trabaja directamente sobre `snr_db`:

```
potencia_banda_dB(t) >= piso_ruido_dB(banda) + margen_dB
  ⟺  potencia_banda_dB(t) - piso_ruido_dB(banda) >= margen_dB
  ⟺  snr_db(t) >= margen_dB
```

Es matemáticamente equivalente para la decisión on/off, y tiene una ventaja adicional: es
robusto a que `piso_ruido_dB` fluctúe trama a trama (estrategia `spectral`), porque `snr_db` ya
incorpora esa fluctuación en cada trama. El parámetro de configuración se llama
`margen_umbral_db` (no `umbral_on_dB`) precisamente para reflejar que es un margen sobre el SNR,
no un nivel absoluto de dBFS.

Config nueva y separada de código: `config/rules_config.json` (política de decisión, no medición
de señal).

```json
{
  "defaults": {
    "margen_umbral_db": 6.0,
    "min_on_frames": 3,
    "min_off_frames": 3,
    "merge_gap_s": 0.5,
    "margen_severidad_medium_db": 6.0,
    "margen_severidad_high_db": 12.0,
    "confianza_escala_db": 10.0
  },
  "bands": {
    "CW_Tone": {},
    "Synth_Burst": {}
  }
}
```

Cada banda hereda `defaults` y puede sobrescribir cualquier clave en `bands.<nombre>`.

## 2. Máquina de estados del evento

Tres estados. El hysteresis simple del Día 13 (on/off con dwell) no alcanza aquí porque una
señal que titila justo en el borde del umbral genera ráfagas de eventos cortos — `COOLDOWN`
existe exactamente para fusionar eso en un solo evento real.

```
IDLE ──(snr_db >= margen_umbral_db durante >= min_on_frames)──▶ ACTIVO   (emite start)
ACTIVO ──(cada trama activa, mientras dure)──▶ ACTIVO                    (actualiza pico/duración)
ACTIVO ──(snr_db < margen_umbral_db durante >= min_off_frames)──▶ COOLDOWN  (no cierra todavía)
COOLDOWN ──(snr_db >= margen_umbral_db de nuevo, dentro de merge_gap_s)──▶ ACTIVO  (fusiona, mismo event_id)
COOLDOWN ──(pasa merge_gap_s sin reactivarse)──▶ IDLE                    (emite close, closed_reason="threshold_off")
```

**Solo las tramas genuinamente activas (`snr_db >= margen_umbral_db`) actualizan
`last_active_t_s`, `pico_dbfs`, `potencia_media_activa_dbfs` y `confianza`.** Las tramas que
caen por debajo del umbral mientras el motor todavía cuenta hacia `min_off_frames` (dwell de
apagado) mantienen el estado en `ACTIVO`, pero no se promedian como si fueran señal — de lo
contrario `duration_s` quedaría inflada por el propio dwell de apagado en vez de reflejar la
extensión real de la emisión.

**Caso de borde obligatorio — corte a mitad de evento:** si la captura termina con un evento en
estado `ACTIVO` o `COOLDOWN`, `EventEngine.flush()` fuerza el cierre con
`closed_reason="end_of_capture"`. Nunca se pierde un evento silenciosamente, pero queda marcado
como truncado, no como cierre natural por umbral. `flush()` debe llamarse exactamente una vez,
después de procesar la última trama de la sesión (lo hace `scripts/run_event_engine.py`).

## 3. Severidad y confianza

**Heurístico simple v0.1, no una probabilidad calibrada.** Los cortes (6dB, 12dB, 10dB de
escala) son valores iniciales razonables, no medidos — se ajustan con datos reales más adelante
si hace falta.

Por la misma razón de la sección 1 (trabajar en espacio SNR en vez de dBFS absoluto), las
fórmulas de severidad y confianza usan el **margen de SNR pico/medio sobre `margen_umbral_db`**,
en vez de `pico_dbfs_evento - umbral_on_dB` en dBFS absoluto (que sería ambiguo si el piso varía
trama a trama):

```
margen_pico_snr_db  = max(snr_db durante el evento) - margen_umbral_db
margen_medio_snr_db = promedio(snr_db durante el evento) - margen_umbral_db

severidad:
  "low"    si margen_pico_snr_db <  margen_severidad_medium_db  (default 6 dB)
  "medium" si margen_severidad_medium_db <= margen_pico_snr_db < margen_severidad_high_db (default 12 dB)
  "high"   si margen_pico_snr_db >= margen_severidad_high_db

confianza = clamp(margen_medio_snr_db / confianza_escala_db, 0.0, 1.0)
  # confianza_escala_db configurable, default 10 dB → a partir de 10dB de SNR medio
  # sobre el margen umbral, confianza = 1.0
```

El campo `pico_dbfs` reportado en el evento es, en cambio, el pico absoluto de la columna
`pico_dbfs` del CSV (Día 13) durante la ventana activa — se reporta en dBFS porque es un valor
que el usuario final quiere leer en unidades físicas, aunque la clasificación de severidad
internamente use el margen de SNR.

## 4. Estructura del objeto Evento

```json
{
    "event_id": "sess_abc123_Synth_Burst_evt_0007",
    "session_id": "sess_abc123",
    "band_name": "Synth_Burst",
    "rule_name": "power_threshold",
    "capture_sha256": "...",
    "start_t_s": 1.502912,
    "end_t_s": 3.503296,
    "duration_s": 2.000384,
    "pico_dbfs": -6.660,
    "potencia_media_activa_dbfs": -6.91,
    "severidad": "high",
    "confianza": 1.0,
    "n_fusiones": 0,
    "closed_reason": "threshold_off"
}
```

`closed_reason` es `"threshold_off"` (cierre natural, la señal cayó bajo el umbral por más de
`merge_gap_s`) o `"end_of_capture"` (cierre forzado, la captura terminó a mitad de una emisión).

`event_id` es secuencial por sesión y banda (`<session_id>_<band_name>_evt_NNNN`) —
determinista, sin UUIDs aleatorios, para que la misma entrada produzca siempre la misma salida
byte a byte. Incluye `band_name` porque cada banda corre su propio `EventEngine` con su propio
contador: sin el nombre de banda, dos eventos de bandas distintas en la misma sesión podrían
compartir `event_id`.

## 5. Estructura de archivos

```
app/events/engine.py           # EventEngine: máquina de estados pura, sin I/O
config/rules_config.json       # umbrales, dwell frames, merge_gap_s, severidad, confianza
scripts/run_event_engine.py    # CLI: features_<sesion>.csv + rules_config.json -> eventos_<sesion>.json
tests/test_events_known.py     # escenarios sintéticos A-F con eventos esperados (golden files). Runner nativo.
tests/golden/*.json            # conjuntos de eventos esperados, guardados una vez y comparados siempre
docs/EVENTS_REF.md             # este documento
```

## 6. Uso

```bash
python3 scripts/run_event_engine.py \
    tests/day13_results/features_captura_106.5MHz_part001_espectrograma.csv \
    --rules-config config/rules_config.json \
    --out-dir tests/day14_results/
```

Genera `eventos_<sesion>.json` en `--out-dir`.

## 7. Escenarios de prueba (tests/test_events_known.py)

| Escenario | Señal sintética | Resultado esperado | Qué prueba |
|---|---|---|---|
| A — burst limpio | 1 burst de 2s, SNR estable sobre el umbral | exactamente 1 evento, duración ~2.0s ±1 trama | caso base |
| B — burst con titileo | 1 burst con un dip que cruza a COOLDOWN y se recupera dentro de `merge_gap_s` | exactamente 1 evento (`n_fusiones=1`), no fragmentado | valida `merge_gap_s` |
| C — dos bursts separados | 2 bursts separados por > `merge_gap_s` | exactamente 2 eventos distintos, `n_fusiones=0` | confirma que el merge no fusiona señales genuinamente separadas |
| D — silencio puro | Solo ruido, sin señal | 0 eventos | sin falsos positivos |
| E — corte a mitad de evento (ACTIVO y COOLDOWN) | Burst que empieza pero el archivo termina antes del cierre natural | 1 evento con `closed_reason="end_of_capture"` | el caso de borde de la sección 2 |
| F — ráfagas cortas separadas | Ráfagas de 5ms separadas por huecos < 15ms y > 15ms | Fusión para < 15ms, Fragmentación para > 15ms | valida `merge_gap_s = 0.015` en `packet_traffic` |

Los eventos esperados se guardan como `tests/golden/*.json` la primera vez que pasan, y las
corridas futuras comparan contra esa referencia con tolerancia de ±1 trama en tiempos y ±0.05
en valores en dB.

## 8. Limitaciones conocidas

- La regla v0.1 es un solo umbral de potencia por banda (`power_threshold`). No detecta
  cambios de forma espectral, saltos de frecuencia, ni modulación — solo presencia/ausencia
  de energía sobre un margen de SNR.
- Severidad y confianza son heurísticos con cortes fijos (6/12 dB, escala 10 dB), no
  probabilidades calibradas contra datos reales.
- El motor procesa una banda a la vez, de forma independiente — no correlaciona eventos entre
  bandas (ej. "esto que empezó en banda A también apareció en banda B").
- `min_on_frames`/`min_off_frames` fijos por banda: no se adaptan dinámicamente a la tasa de
  tramas por segundo de la sesión. Si `hop`/`fs` cambian drásticamente, puede ser necesario
  reajustar estos valores en `rules_config.json`.

## 9. Pruebas y CI (Entrypoint Canónico)

El entorno Docker nativo del proyecto (`harogic_final`) puede tener conflictos con `pytest` y ciertos plugins heredados (ej. `libtmux`). Por instrucción expresa del equipo, **no se utiliza pytest como motor de CI**. 

El *entrypoint* canónico para validación es el runner *standalone* construido dentro del mismo script de pruebas. Para ejecutar la suite completa de escenarios sintéticos (A-F):
```bash
docker exec harogic_final python3 /workspace/tests/test_events_known.py
```
Este diseño minimiza dependencias y friction en entornos aislados.
