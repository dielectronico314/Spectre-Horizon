from fastapi import FastAPI, HTTPException, Query, APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from typing import List, Optional
from datetime import date
from pydantic import ValidationError

from app.api.db import get_db_connection, init_db
from app.api.models import HealthResponse, SensorStatusResponse, SessionResponse, SessionDetailResponse, EventoResponse, EvidenceLinks
from app.api.security import get_evidence_path
from app.dashboard.main import mount_dashboard

tags_metadata = [
    {"name": "General", "description": "Endpoints de salud y estado del sistema."},
    {"name": "Sesiones", "description": "Capturas indexadas, con filtro por fecha."},
    {"name": "Eventos", "description": "Detecciones del motor de reglas (Día 14)."},
    {"name": "Evidencia", "description": "Referencias seguras a paquetes forenses (Día 15)."},
]

app = FastAPI(
    title="Cenital RF Spectrum API",
    description="API de consulta para sesiones de captura, eventos detectados y evidencia forense de RF.",
    version="0.1.0",
    contact={"name": "Cenital", "url": "https://github.com/cenital"},
    openapi_tags=tags_metadata
)

@app.exception_handler(HTTPException)
async def error_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.status_code, "message": exc.detail}}
    )

@app.on_event("startup")
def startup_event():
    init_db()

@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

api_router = APIRouter(prefix="/api/v1")

@api_router.get("/health", response_model=HealthResponse, tags=["General"])
def health_check():
    """Verifica que el proceso esté vivo y la BD conectada."""
    try:
        conn = get_db_connection()
        conn.execute("SELECT 1").fetchone()
        conn.close()
        return {"status": "ok", "version": "0.1.0"}
    except Exception as e:
        raise HTTPException(status_code=500, detail="Database connection failed")

@api_router.get("/sensor/status", response_model=SensorStatusResponse, tags=["General"])
def sensor_status():
    """
    Retorna el estado de la última sesión conocida.
    No asume que el sensor esté escaneando en vivo a menos que exista un mecanismo explícito para ello.
    """
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT session_id, start_datetime FROM sessions ORDER BY start_datetime DESC LIMIT 1").fetchone()
        count_row = conn.execute("SELECT COUNT(*) as c FROM events").fetchone()
        
        ultima_sesion = row["session_id"] if row else None
        ultima_captura_utc = row["start_datetime"] if row else None
        eventos_totales = count_row["c"] if count_row else 0
        
        return {
            "ultima_sesion": ultima_sesion,
            "ultima_captura_utc": ultima_captura_utc,
            "en_vivo": False,
            "eventos_totales": eventos_totales
        }
    finally:
        conn.close()

@api_router.get("/sessions", response_model=List[SessionResponse], tags=["Sesiones"])
def list_sessions(
    desde: Optional[date] = Query(None, description="Filtrar sesiones desde esta fecha (inclusive)"),
    hasta: Optional[date] = Query(None, description="Filtrar sesiones hasta esta fecha (inclusive)")
):
    conn = get_db_connection()
    try:
        query = "SELECT * FROM sessions WHERE 1=1"
        params = []
        if desde:
            query += " AND start_datetime >= ?"
            params.append(desde.isoformat())
        if hasta:
            query += " AND start_datetime <= ?"
            params.append(hasta.isoformat() + "T23:59:59Z")
            
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

@api_router.get("/sessions/{session_id}", response_model=SessionDetailResponse, tags=["Sesiones"])
def get_session(session_id: str):
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Sesión no encontrada")
            
        events_rows = conn.execute("SELECT event_id FROM events WHERE session_id = ?", (session_id,)).fetchall()
        
        result = dict(row)
        result["eventos"] = [er["event_id"] for er in events_rows]
        return result
    finally:
        conn.close()

@api_router.get("/events", response_model=List[EventoResponse], tags=["Eventos"])
def list_events(
    banda: Optional[str] = None,
    severidad: Optional[str] = None,
    desde: Optional[date] = None,
    hasta: Optional[date] = None
):
    if severidad and severidad not in ["low", "medium", "high"]:
        raise HTTPException(status_code=422, detail="severidad debe ser 'low', 'medium' o 'high'")

    conn = get_db_connection()
    try:
        query = """
            SELECT e.* 
            FROM events e
            JOIN sessions s ON e.session_id = s.session_id
            WHERE 1=1
        """
        params = []
        
        if banda:
            query += " AND e.band_name = ?"
            params.append(banda)
        if severidad:
            query += " AND e.severidad = ?"
            params.append(severidad)
        if desde:
            query += " AND s.start_datetime >= ?"
            params.append(desde.isoformat())
        if hasta:
            query += " AND s.start_datetime <= ?"
            params.append(hasta.isoformat() + "T23:59:59Z")
            
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()

@api_router.get("/events/{event_id}", response_model=EventoResponse, tags=["Eventos"])
def get_event(event_id: str):
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT * FROM events WHERE event_id = ?", (event_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Evento no encontrado")
        return dict(row)
    finally:
        conn.close()

@api_router.get("/events/{event_id}/evidence", response_model=EvidenceLinks, tags=["Evidencia"])
def get_evidence_links(event_id: str):
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT 1 FROM events WHERE event_id = ?", (event_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Evento no encontrado")
    finally:
        conn.close()
        
    return {
        "event_id": event_id,
        "archivos": {
            "manifest": f"/api/v1/events/{event_id}/evidence/manifest.json",
            "resumen": f"/api/v1/events/{event_id}/evidence/resumen.md",
            "espectrograma": f"/api/v1/events/{event_id}/evidence/espectrograma_evento.png",
            "iq_selectivo": f"/api/v1/events/{event_id}/evidence/evento.sigmf-data",
            "iq_meta": f"/api/v1/events/{event_id}/evidence/evento.sigmf-meta",
            "features": f"/api/v1/events/{event_id}/evidence/features_evento.csv"
        }
    }

@api_router.get("/events/{event_id}/evidence/{filename:path}", tags=["Evidencia"])
def download_evidence(event_id: str, filename: str):
    """
    Descarga un archivo específico del paquete de evidencia.
    La validación de seguridad se realiza en get_evidence_path.
    """
    file_path = get_evidence_path(event_id, filename)
    return FileResponse(file_path)

@api_router.get("/sessions/{session_id}/waterfall", tags=["Sesiones"])
def get_session_waterfall(session_id: str):
    """
    Retorna el espectrograma (waterfall) estático del bloque más reciente de la sesión.
    """
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT ruta_meta FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        if not row or not row["ruta_meta"]:
            raise HTTPException(status_code=404, detail="Sesión no encontrada o sin metadata")
            
        ruta_meta = row["ruta_meta"]
        meta_path = Path("/workspace") / ruta_meta
        if not meta_path.exists():
            raise HTTPException(status_code=404, detail="Metadata original no encontrada")
            
        # Reemplazar extensión (.sigmf-meta) por _espectrograma.png
        png_path = meta_path.with_name(meta_path.stem.replace(".sigmf-meta", "") + "_espectrograma.png")
        if not png_path.exists():
            raise HTTPException(status_code=404, detail="Espectrograma no encontrado")
            
        return FileResponse(png_path)
    finally:
        conn.close()

app.include_router(api_router)

mount_dashboard(app)
