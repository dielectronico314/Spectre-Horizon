# Deployment — Días 16-17

## Stack

- **API & Dashboard Unificados**: FastAPI en puerto 8000 (`app/api/main.py`)
- **BD**: SQLite (ruta: configurable en `app/api/db.py`)

## Desarrollo — Proceso Único Unificado

```bash
# Terminal 1: API (incluye Dashboard montado en /dashboard/)
python -m uvicorn app.api.main:app --port 8000 --reload
```

O en un comando, usando el script de docker (Vía oficial Día 19):
```bash
bash run_demo.sh
```

### URLs

| Servicio | URL | Docs |
|----------|-----|------|
| API | `http://localhost:8000/api/v1` | `http://localhost:8000/docs` |
| Dashboard | `http://localhost:8000/dashboard` | — |

## Arquitectura de Datos

```
Cliente HTTP (navegador/curl)
    |
    ├─> API :8000
    |   ├─ /health              (status)
    |   ├─ /sensor/status       (estado sensor)
    |   ├─ /sessions            (listado captures)
    |   ├─ /events              (listado eventos)
    |   └─ /events/{id}/evidence (downloads)
    |
    └─> Dashboard :8001
        ├─ /dashboard/          (estado sensor)
        ├─ /dashboard/eventos   (tabla eventos)
        └─ /dashboard/eventos/{event_id} (detalle)
        
        [Dashboard hace HTTP requests a API :8000]
```

Dashboard es cliente de API. Cero acceso directo a BD.

## Producción

Todo el stack vive ahora dentro del contenedor de Docker, el cual expone un puerto unificado:
```bash
# Iniciar contenedor Docker (API + Dashboard integrados)
bash run_demo.sh
```

## Testing

```bash
# Tests de API y Dashboard
python tests/test_api_critical.py
python tests/test_dashboard_flujo.py
```

## Configuración Mínima

### app/api/db.py
Define ruta de SQLite:
```python
DB_PATH = "./cenital.db"  # o /data/cenital.db en producción
```

### app/dashboard/main.py
Define URL de API:
```python
API_BASE = "http://localhost:8000/api/v1"
# Para producción remota: "http://api.internal.cenital:8000/api/v1"
```

### Dependencias
```bash
pip install -r requirements.txt
```

## Logs & Debugging

API & Dashboard unificados:
```bash
# Con DEBUG
python -m uvicorn app.api.main:app --port 8000 --reload --log-level debug
```

## Health Checks

```bash
# API viva?
curl http://localhost:8000/api/v1/health

# Dashboard responde?
curl http://localhost:8000/dashboard/
```

## Roadmap Futuro (Post-Día 17)

- [ ] **Día 18**: Streaming en vivo (WebSocket, waterfall)
- [ ] **Día 19**: Demonio orquestador (limpieza, rotación logs)
- [ ] **Día 20**: Auth (API keys, caducidad)

---
