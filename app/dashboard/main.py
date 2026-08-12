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
    get_severidad, get_confianza_label, get_closed_reason, explain_evento,
    get_spectrum_category, format_freq_mhz
)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

# Configuración de Jinja2
TEMPLATE_DIR = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))
templates.env.globals.update({
    "get_spectrum_category": get_spectrum_category,
    "format_freq_mhz": format_freq_mhz,
})

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

    sessions = await get_from_api("/sessions")
    
    # Offline fallback logic: if offline, force session_golden_demo_v1 to the front if it exists
    ultima_sesion = None
    if status.get("status") != "online" and sessions:
        for s in sessions:
            if s.get("session_id") == "session_golden_demo_v1":
                ultima_sesion = s
                break
                
    if not ultima_sesion:
        ultima_sesion = sessions[0] if sessions else None
    sessions_count = len(sessions) if sessions else 0

    return templates.TemplateResponse(
        request=request,
        name="estado.html",
        context={
            "section": "estado",
            "status": status,
            "ultima_sesion": ultima_sesion,
            "sessions_count": sessions_count,
        }
    )


@router.get("/sesiones", name="dashboard_sesiones")
async def dashboard_sesiones(request: Request):
    """Explorador de Sesiones (todas las capturas)."""
    sesiones = await get_from_api("/sessions")
    return templates.TemplateResponse(
        request=request,
        name="sesiones.html",
        context={
            "section": "sesiones",
            "sesiones": sesiones
        }
    )


@router.get("/sesiones/{session_id}", name="dashboard_sesion_detalle")
async def dashboard_sesion_detalle(request: Request, session_id: str):
    """Vista detallada de una sesión (2D/3D)."""
    try:
        session = await get_from_api(f"/sessions/{session_id}")
    except Exception:
        raise HTTPException(status_code=404, detail="Sesión no encontrada")

    return templates.TemplateResponse(
        request=request,
        name="sesion_detalle.html",
        context={
            "section": "sesiones",
            "session": session
        }
    )


@router.get("/eventos", name="dashboard_eventos")
async def dashboard_eventos(
    request: Request,
    banda: str = None,
    espectro: str = None,
    frecuencia_mhz: str = None,
    severidad: str = None,
    desde: str = None,
    hasta: str = None,
):
    """Tabla de eventos con filtros."""
    params = {}
    if banda:
        params["banda"] = banda
    if espectro:
        params["espectro"] = espectro
    if frecuencia_mhz and frecuencia_mhz.strip():
        try:
            params["frecuencia_mhz"] = float(frecuencia_mhz)
        except ValueError:
            pass
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

    # Extraer lista de bandas únicas (Modo Experto)
    bandas = set(e.get("band_name") for e in eventos if e.get("band_name"))
    bandas = sorted(bandas)

    # Extraer lista de frecuencias exactas de TODAS las sesiones
    all_sessions = await get_from_api("/sessions")
    frecuencias = set()
    for s in all_sessions:
        if s.get("fc_hz"):
            mhz = round(s["fc_hz"] / 1e6, 2)
            frecuencias.add(mhz)
    frecuencias = sorted(frecuencias)
    
    espectros_disponibles = ["HF", "VHF", "UHF", "SHF"]

    # Filtrar destacados: excluir LO Leakage (offset == 0 o cercano) y deduplicar bloque espectral solapado
    destacados_crudos = [e for e in eventos if e.get("severidad") == "high"]
    
    # Excluir fugas del oscilador local (LO Leakage) - requiere cruzar con features_config en el futuro
    # destacados_crudos = [e for e in destacados_crudos if abs(e.get("freq_offset_hz", 999.0)) > 1.0]
    
    # Agrupar por solapamiento de tiempo (eventos que empiezan y duran casi lo mismo son el mismo fenómeno en bandas adyacentes)
    destacados_final = []
    for e in destacados_crudos:
        is_duplicate = False
        for d in destacados_final:
            if e.get("session_id") == d.get("session_id"):
                time_diff = abs(e.get("start_t_s", 0) - d.get("start_t_s", 0))
                dur_diff = abs(e.get("duration_s", 0) - d.get("duration_s", 0))
                
                band_e = e.get("band_name", "")
                band_d = d.get("band_name", "")
                
                # Frecuencias adyacentes: si son exactamente la misma banda, o ambas son del bloque adyacente FM_Sub
                es_banda_adyacente = (band_e == band_d) or (band_e.startswith("FM_Sub") and band_d.startswith("FM_Sub"))
                
                if time_diff < 0.1 and dur_diff < 0.1 and es_banda_adyacente:
                    is_duplicate = True
                    # Conservar el de mayor pico
                    if e.get("pico_dbfs", -999) > d.get("pico_dbfs", -999):
                        d.update(e)
                    break
        if not is_duplicate:
            destacados_final.append(e)

    return templates.TemplateResponse(
        request=request,
        name="eventos.html",
        context={
            "section": "eventos",
            "eventos": eventos,
            "bandas": bandas,
            "frecuencias": frecuencias,
            "espectros_disponibles": espectros_disponibles,
            "filtro_banda": banda or "",
            "filtro_espectro": espectro or "",
            "filtro_frecuencia": frecuencia_mhz or "",
            "filtro_severidad": severidad or "",
            "filtro_desde": desde or "",
            "filtro_hasta": hasta or "",
            "destacados": destacados_final,
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
        request=request,
        name="evento_detalle.html",
        context={
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
