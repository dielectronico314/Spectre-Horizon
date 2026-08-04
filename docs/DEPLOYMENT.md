# Deployment — Días 16-17

## Stack

- **API**: FastAPI en puerto 8000 (`app/api/main.py`)
- **Dashboard**: FastAPI en puerto 8001 (`app/dashboard/server.py`)
- **BD**: SQLite (ruta: configurable en `app/api/db.py`)

## Desarrollo — Dos Procesos en Paralelo

```bash
# Terminal 1: API
python -m uvicorn app.api.main:app --port 8000 --reload

# Terminal 2: Dashboard (cliente HTTP a API)
python -m uvicorn app.dashboard.server:app --port 8001 --reload
```

O en un comando:
```bash
bash run_servers.sh
```

### URLs

| Servicio | URL | Docs |
|----------|-----|------|
| API | `http://localhost:8000/api/v1` | `http://localhost:8000/docs` |
| Dashboard | `http://localhost:8001/dashboard` | — |

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

Opción A: Misma máquina, dos procesos
```bash
# Supervisor/systemd: API en :8000
# Supervisor/systemd: Dashboard en :8001
# Nginx reverse proxy (opcional)
```

Opción B: Máquinas separadas
```bash
# Server A: app.api.main en :8000
# Server B: app.dashboard.server en :8001
# Actualizar API_BASE en humanize.py (ej: "http://api.internal:8000/api/v1")
```

## Testing

```bash
# Tests de API
python tests/test_api_critical.py

# Tests de Dashboard
python tests/test_dashboard_flujo.py

# Ambos (Dashboard monta también en API :8000 para compatibilidad)
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

API:
```bash
# Con DEBUG
python -m uvicorn app.api.main:app --port 8000 --reload --log-level debug
```

Dashboard:
```bash
# Logs de HTTP requests a API
python -m uvicorn app.dashboard.server:app --port 8001 --reload --log-level debug
```

## Health Checks

```bash
# API viva?
curl http://localhost:8000/api/v1/health

# Dashboard puede alcanzar API?
# (Automático: si `/dashboard/` falla, es porque API no responde)
curl http://localhost:8001/dashboard/
```

## Roadmap Futuro (Post-Día 17)

- [ ] **Día 18**: Streaming en vivo (WebSocket, waterfall)
- [ ] **Día 19**: Demonio orquestador (limpieza, rotación logs)
- [ ] **Día 20**: Auth (API keys, caducidad)

---

**Nota**: Las versiones de `mount_dashboard()` en API (para desarrollo) y `app/dashboard/server.py` (para producción) son equivalentes. En desarrollo se usa ambos por conveniencia; en producción elegir uno según escala.
