"""
app/dashboard/main.py — Rutas del dashboard renderizado con Jinja2.
Cliente HTTP sobre la API del Día 16. Cero acceso directo a BD, cero recomputación.
"""

from fastapi import APIRouter, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import httpx
from datetime import datetime

from app.dashboard.humanize import (
    get_severidad, get_confianza_label, get_closed_reason, explain_evento
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# Configuración de Jinja2
TEMPLATE_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

# URL base de la API del Día 16 (running en localhost)
API_BASE = "http://localhost:8000/api/v1"

async def get_from_api(endpoint: str, params: dict = None) -> dict:
    """Fetch datos de la API del Día 16."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            url = f"{API_BASE}{endpoint}"
            response = await client.get(url, params=params)
            response.raise_for_status()
            return response.json()
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"API no disponible: {str(e)}")


@router.get("/", name="dashboard_estado")
async def dashboard_estado(request: Request):
    """Pantalla de estado del sensor."""
    status = await get_from_api("/sensor/status")

    # Obtener última sesión (el endpoint /sensor/status ya incluye info, pero tomamos todas y usamos la última)
    sessions = await get_from_api("/sessions")
    ultima_sesion = sessions[0] if sessions else None
    sessions_count = len(sessions) if sessions else 0

    return templates.TemplateResponse(
        "estado.html",
        {
            "request": request,
            "section": "estado",
            "status": status,
            "ultima_sesion": ultima_sesion,
            "sessions_count": sessions_count,
        }
    )


@router.get("/eventos", name="dashboard_eventos")
async def dashboard_eventos(
    request: Request,
    banda: str = None,
    severidad: str = None,
    desde: str = None,
    hasta: str = None,
):
    """Tabla de eventos con filtros."""
    params = {}
    if banda:
        params["banda"] = banda
    if severidad:
        params["severidad"] = severidad
    if desde:
        params["desde"] = desde
    if hasta:
        params["hasta"] = hasta

    eventos = await get_from_api("/events", params=params if params else None)

    # Enriquecer cada evento con datos de sesión para mostrar fecha
    for ev in eventos:
        try:
            session = await get_from_api(f"/sessions/{ev['session_id']}")
            ev["session"] = session
        except:
            ev["session"] = None

    # Extraer lista de bandas únicas para el dropdown de filtros
    bandas = set(e.get("band_name") for e in eventos if e.get("band_name"))
    bandas = sorted(bandas)

    return templates.TemplateResponse(
        "eventos.html",
        {
            "request": request,
            "section": "eventos",
            "eventos": eventos,
            "bandas": bandas,
            "filtro_banda": banda or "",
            "filtro_severidad": severidad or "",
            "filtro_desde": desde or "",
            "filtro_hasta": hasta or "",
        }
    )


@router.get("/eventos/{event_id}", name="dashboard_evento_detalle")
async def dashboard_evento_detalle(request: Request, event_id: str):
    """Detalle de un evento individual."""
    evento = await get_from_api(f"/events/{event_id}")

    # Obtener enlaces de evidencia
    evidence_links_response = await get_from_api(f"/events/{event_id}/evidence")
    evidence_links = evidence_links_response.get("archivos", {})

    # Humanizar
    severidad_obj = get_severidad(evento.get("severidad", "low"))
    severidad_desc = severidad_obj["descripcion"]
    confianza = evento.get("confianza", 0.0)
    confianza_label = get_confianza_label(confianza)
    closed_reason_label = get_closed_reason(evento.get("closed_reason", "unknown"))
    explicacion = explain_evento(evento)

    return templates.TemplateResponse(
        "evento_detalle.html",
        {
            "request": request,
            "section": "eventos",
            "evento": evento,
            "severidad_desc": severidad_desc,
            "confianza_label": confianza_label,
            "closed_reason_label": closed_reason_label,
            "explicacion": explicacion,
            "evidence_links": evidence_links,
        }
    )


def mount_dashboard(app):
    """
    Monta el dashboard router en la app FastAPI existente del Día 16.
    Llamar desde app/api/main.py después de crear la app.
    """
    app.include_router(router)

    # Montar static files si existen
    static_dir = Path(__file__).parent / "static"
    if static_dir.exists():
        app.mount("/dashboard/static", StaticFiles(directory=str(static_dir)), name="dashboard_static")
