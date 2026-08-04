"""
app/dashboard/server.py — Dashboard standalone en puerto 8001.

App FastAPI que SOLO monta dashboard. Cliente HTTP a API en :8000.
Escalable independiente de API.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from app.dashboard.main import router

app = FastAPI(
    title="Cenital Dashboard",
    description="Monitor RF/SDR — estado sensor, eventos, evidencia forense"
)

# Incluir rutas del dashboard
app.include_router(router)

# Montar static files si existen
static_dir = Path(__file__).parent / "static"
if static_dir.exists():
    app.mount("/dashboard/static", StaticFiles(directory=str(static_dir)), name="dashboard_static")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
