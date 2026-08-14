from fastapi import FastAPI, HTTPException, Query, APIRouter, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from typing import List, Optional
from datetime import date
from pydantic import ValidationError
from pathlib import Path
from starlette.concurrency import run_in_threadpool
import sys

# Agregar ruta de scripts al PYTHONPATH para importar probe_device
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(PROJECT_ROOT))
import subprocess
import json

WORKSPACE_DIR = Path("/workspace") if Path("/workspace").exists() else PROJECT_ROOT

from app.api.db import get_db_connection, init_db
from app.api.models import HealthResponse, SensorStatusResponse, SessionResponse, SessionDetailResponse, EventoResponse, EvidenceLinks
from app.api.security import get_evidence_path
from app.dashboard.main import mount_dashboard
from app.reports.generator import generate_report_html

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

def _check_hardware_cached():
    import time
    import json
    import os
    
    cache_file = "/tmp/harogic_hw_cache.json"
    now = time.time()
    
    # Intenta leer el caché
    if os.path.exists(cache_file):
        try:
            with open(cache_file, "r") as f:
                data = json.load(f)
            if now - data.get("timestamp", 0) < 5:
                return data.get("sensor_conectado", False)
        except Exception:
            pass
            
    sensor_conectado = False
    try:
        res = subprocess.run(
            ["python3", str(PROJECT_ROOT / "scripts" / "probe_device.py")],
            capture_output=True, text=True, timeout=10
        )
        if res.returncode == 0:
            stdout = res.stdout
            json_start = stdout.find('{')
            if json_start != -1:
                parsed = json.loads(stdout[json_start:])
                sensor_conectado = parsed.get("status") == "success"
    except Exception:
        pass
        
    # Escribe el caché
    try:
        with open(cache_file, "w") as f:
            json.dump({"timestamp": now, "sensor_conectado": sensor_conectado}, f)
    except Exception:
        pass
        
    return sensor_conectado

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
        
        # Consultar la conectividad real del hardware mediante subprocess con caché de 5s
        sensor_conectado = _check_hardware_cached()
        
        sensor_fresco = False
        if ultima_captura_utc:
            try:
                from datetime import datetime, timezone
                dt_str = ultima_captura_utc.replace("Z", "+00:00")
                dt = datetime.fromisoformat(dt_str)
                now_utc = datetime.now(timezone.utc)
                delta_s = (now_utc - dt).total_seconds()
                sensor_fresco = 0 <= delta_s < 300
            except Exception:
                pass
                
        return {
            "ultima_sesion": ultima_sesion,
            "ultima_captura_utc": ultima_captura_utc,
            "en_vivo": False,
            "eventos_totales": eventos_totales,
            "sensor_conectado": sensor_conectado,
            "sensor_fresco": sensor_fresco
        }
    finally:
        conn.close()

@api_router.get("/sensor/health", tags=["General"])
async def sensor_health():
    """
    Retorna el estado en tiempo real del hardware conectándose mediante SoapySDR.
    """
    res = await run_in_threadpool(probe)
    return res

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
            
        query += " ORDER BY start_datetime DESC"
            
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
    hasta: Optional[date] = None,
    espectro: Optional[str] = None,
    frecuencia_mhz: Optional[float] = None
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
        
        if espectro:
            espectro = espectro.upper()
            if espectro == "HF":
                query += " AND s.fc_hz >= 3e6 AND s.fc_hz < 30e6"
            elif espectro == "VHF":
                query += " AND s.fc_hz >= 30e6 AND s.fc_hz < 300e6"
            elif espectro == "UHF":
                query += " AND s.fc_hz >= 300e6 AND s.fc_hz < 3000e6"
            elif espectro == "SHF":
                query += " AND s.fc_hz >= 3000e6 AND s.fc_hz < 30000e6"

        if frecuencia_mhz is not None:
            # Tolerancia de +/- 0.1 MHz para evitar problemas de precisión flotante
            fc_hz = frecuencia_mhz * 1e6
            query += " AND s.fc_hz >= ? AND s.fc_hz <= ?"
            params.extend([fc_hz - 100000, fc_hz + 100000])
            
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
        meta_path = WORKSPACE_DIR / ruta_meta
        if not meta_path.exists():
            raise HTTPException(status_code=404, detail="Metadata original no encontrada")
            
        # Reemplazar extensión (.sigmf-meta) por _espectrograma.png
        png_path = meta_path.with_name(meta_path.stem.replace(".sigmf-meta", "") + "_espectrograma.png")
        if not png_path.exists():
            raise HTTPException(status_code=404, detail="Espectrograma no encontrado")
            
        return FileResponse(png_path)
    finally:
        conn.close()

@api_router.get("/sessions/{session_id}/waterfall_thumb", tags=["Sesiones"])
def get_session_waterfall_thumb(session_id: str):
    """
    Retorna la miniatura del espectrograma de la sesión, o el espectrograma completo si la miniatura no existe.
    """
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT ruta_meta FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        if not row or not row["ruta_meta"]:
            raise HTTPException(status_code=404, detail="Sesión no encontrada o sin metadata")
            
        ruta_meta = row["ruta_meta"]
        meta_path = WORKSPACE_DIR / ruta_meta
        if not meta_path.exists():
            raise HTTPException(status_code=404, detail="Metadata original no encontrada")
            
        # Intentar cargar _thumb.png
        thumb_path = meta_path.with_name(meta_path.stem.replace(".sigmf-meta", "") + "_thumb.png")
        if thumb_path.exists():
            return FileResponse(thumb_path)
            
        # Fallback al espectrograma normal
        png_path = meta_path.with_name(meta_path.stem.replace(".sigmf-meta", "") + "_espectrograma.png")
        if png_path.exists():
            return FileResponse(png_path)
            
        raise HTTPException(status_code=404, detail="Thumbnail ni espectrograma encontrados")
    finally:
        conn.close()

@api_router.get("/sessions/{session_id}/waterfall3d.json", tags=["Sesiones"])
def get_session_waterfall3d(session_id: str):
    """
    Retorna el espectrograma (waterfall) en formato JSON 3D decimado.
    """
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT ruta_meta FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        if not row or not row["ruta_meta"]:
            raise HTTPException(status_code=404, detail="Sesión no encontrada o sin metadata")
            
        ruta_meta = row["ruta_meta"]
        meta_path = WORKSPACE_DIR / ruta_meta
        if not meta_path.exists():
            raise HTTPException(status_code=404, detail="Metadata original no encontrada")
            
        # Reemplazar extensión (.sigmf-meta) por _waterfall3d.json
        json_path = meta_path.with_name(meta_path.stem.replace(".sigmf-meta", "") + "_waterfall3d.json")
        if not json_path.exists():
            raise HTTPException(status_code=404, detail="El espectrograma 3D no se generó para esta captura")
            
        return FileResponse(json_path, media_type="application/json")
    finally:
        conn.close()

@api_router.post("/sessions/{session_id}/reporte", tags=["Sesiones"])
def generate_report_endpoint(session_id: str, request: Request):
    """
    Genera y devuelve el HTML del reporte para una sesión específica al vuelo, 
    sin guardarlo en disco en el servidor.
    """
    try:
        # Generar contenido
        html_content = generate_report_html(session_id)
        
        # Devolver directamente como archivo adjunto (al vuelo)
        headers = {"Content-Disposition": f'attachment; filename="reporte_{session_id}.html"'}
        return Response(content=html_content, media_type="text/html", headers=headers)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

app.include_router(api_router)

mount_dashboard(app)
