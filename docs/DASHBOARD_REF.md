# Dashboard Mínimo — Día 17

## Objetivo

Interfaz web para ver estado del sensor, eventos detectados y evidencia forense. Construido para audiencia no técnica: no requiere conocer dBFS, SNR o máquinas de estados. Usa solo API del Día 16 como fuente de datos — cero acceso directo a BD.

## Arquitectura

**Stack:** Jinja2 (templates) + FastAPI (servidor) + vanilla CSS. No SPA, no Node.js build, no estado de cliente.

**Decisión:** Server-rendered porque:
- FastAPI ya corre (Día 16) → Jinja2 es cero costo
- "Sin interfaz compleja" significa no agregar el overhead de bundler/React
- Si en futuro se necesita reactividad viva, se agrega HTMX sin refactorizar

**Instalación en app existente:**
```python
from app.dashboard.main import mount_dashboard
mount_dashboard(app)  # después de app.include_router(api_router)
```

## Rutas

| Ruta | Template | Función |
|------|----------|---------|
| `/dashboard/` | `estado.html` | Estado del sensor, última sesión, advertencia de interrupciones |
| `/dashboard/eventos` | `eventos.html` | Tabla de eventos con filtros (banda, severidad, fecha) |
| `/dashboard/eventos/{event_id}` | `evento_detalle.html` | Detalle de 1 evento + explicación humanizada + enlaces evidencia |

## Traducción de Jerga (`humanize.py`)

Mapeo central: dato técnico → frase comprensible. **Cambiar redacción = 1 lugar.**

```python
# Ejemplo: severidad
"high" → "🔴 Alta — Señal muy fuerte, muy por encima del ruido"

# Explicación automática de evento
explain_evento(evento) 
→ "La potencia detectada en FM_106.5 superó el piso de ruido 
   por aproximadamente 13 dB durante 2.03 segundos. 
   Esto se clasifica como señal muy fuerte."
```

Tabla completa en `humanize.py` sección "SEVERIDAD_LABELS", "CLOSED_REASON_LABELS", etc.

## tuvo_interrupciones — Detección Sin Instrumentación Nueva

Problema: "mostrar errores del sensor" requiere saber si hubo desconexiones durante captura.

Solución: Detectar gaps temporales entre eventos. Implementado en `build_index.py`:

```python
def detect_interrupciones(eventos):
    """Si hay gap > 5s entre eventos, probablemente hubo interrupción."""
    for i in range(len(sorted_eventos) - 1):
        gap = start_siguiente - end_actual
        if gap > 5.0:
            return True
```

Resultado guardado en `sessions.tuvo_interrupciones` (nuevo campo Día 17). Mostrado en pantalla de estado con ⚠️ y texto llano.

## Flujo Usuario No Técnico

1. **Abre `/dashboard/`** → Ve estado (verde=ok, amarillo=interrupciones, rojo=problema) + última frecuencia capturada
2. **Click en "Ver eventos"** → Tabla de todos los eventos con filtros
3. **Filtra por severidad "Alta"** → Ve sólo eventos 🔴
4. **Click en un evento** → Abre detalle con:
   - "¿Por qué se generó?" en lenguaje llano (sin dBFS crudos)
   - Botones para descargar espectrograma, manifiesto, etc.
   - Si detectó interrupciones en la captura, dice "_se detectaron 3 pausas cortas, contadas como 1 evento_"

## Criterios de Terminación ✓

- [x] Las 5 pantallas existen y son navegables (estado, tabla, detalle, y ahora dashboard mismo)
- [x] Bloque "¿Por qué?" usa `humanize.py`, no dBFS crudos
- [x] `tuvo_interrupciones` visible en estado con ⚠️
- [x] Test `test_flujo_completo_no_tecnico` navega estado → eventos → detalle → evidencia
- [x] API Día 16 ahora retorna `tuvo_interrupciones` en respuesta sessions

## Datos que Fluyen

```
API /sensor/status
├─ status.en_vivo (boolean)
├─ status.eventos_totales
└─ status.ultima_sesion

API /sessions/{id}
├─ fc_hz, fs_hz, start_datetime
└─ tuvo_interrupciones ← NUEVO

API /events/{event_id}
├─ pico_dbfs, potencia_media_activa_dbfs
├─ severidad, confianza
├─ closed_reason, duration_s
└─ [fed a humanize.py para traducción]

API /events/{event_id}/evidence
└─ archivos: { manifest, espectrograma, iq, ... }
```

## CSS

Incluido inline en `base.html`. Responsive (flex, grid), light/dark pseudo-support. **Sin framework pesado** (Tailwind, Bootstrap). Total ~1500 líneas CSS. Si cambia en futuro, está en un único <style> block.

## Testing

Ejecutar:
```bash
python tests/test_dashboard_flujo.py
```

Valida:
- Pantalla de estado renderiza sin error
- Tabla tiene filtros funcionales
- Detalle de evento abre y muestra explicación
- Sin links rotos
- HTML válido

**Nota:** Test usa `/dashboard/` directo via TestClient, no requiere Selenium.

## Mejoras Futuras (Fuera de Alcance Día 17)

- Waterfall en vivo (streaming, requiere WebSocket/Demonio Orquestador, Días 18-19)
- Visualización 3D del espectrograma (encaja en 3.2 si hay presupuesto)
- Auto-refresh con HTMX (botón "Actualizar" hace GET silencioso)
- Exportar sesión a CSV/PDF

## Notas de Integración

1. **Dependencia nueva:** `httpx` (async HTTP client) — ya en requirements.py si está.
2. **CORS:** No necesario (dashboard es mismo dominio que API, ambas en localhost:8000).
3. **Auth:** No implementado (Día 17 es MVP, sensor asume red local confiable).
4. **Reinicio:** Si API del Día 16 se cae, dashboard muestra error 503 "API no disponible".

## El Requisito Oficial, Mapeado

> **"Terminado cuando: una persona no técnica identifica el estado del sensor, abre un evento y entiende por qué se generó."**

✓ **Estado:** Home muestra 🟢/⚠️/🔴 sin jerga. Última frecuencia en MHz.
✓ **Abre evento:** Tabla clickeable, detalle renderizado.
✓ **Entiende por qué:** Bloque "¿Por qué se generó?" traduce dBFS a "superó el piso por X dB durante Y segundos".

Test `test_flujo_completo_no_tecnico` demuestra exactamente esto: navega estados → eventos → detalle → lee explicación.
