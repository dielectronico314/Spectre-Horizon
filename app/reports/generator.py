import sqlite3
import json
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

# Intentar resolver PROJECT_ROOT
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

# Mock de dependencias si no estamos ejecutando dentro del proyecto completo
import sys
sys.path.append(str(PROJECT_ROOT))
from app.api.db import get_db_connection
from app.dashboard.humanize import explain_evento, get_severidad

def get_session_data(session_id: str) -> dict:
    conn = get_db_connection()
    try:
        # Extraer sesión
        row_ses = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
        if not row_ses:
            raise ValueError(f"Sesión no encontrada: {session_id}")
        
        session = dict(row_ses)
        
        # Extraer eventos de esta sesión
        rows_evt = conn.execute("SELECT * FROM events WHERE session_id = ? ORDER BY start_t_s ASC", (session_id,)).fetchall()
        eventos = [dict(r) for r in rows_evt]
        
        # Extraer manifests para hashes
        hashes = {}
        for evt in eventos:
            ruta_meta = evt.get("ruta_evidencia")
            if ruta_meta:
                manifest_path = Path("/workspace") / ruta_meta.replace(".json", "_manifest.json")
                if manifest_path.exists():
                    try:
                        manifest = json.loads(manifest_path.read_text())
                        hashes[evt["event_id"]] = manifest.get("data_hash", "No disponible")
                    except Exception:
                        pass
                        
            # Humanizar evento
            evt["explicacion"] = explain_evento(evt)
            evt["severidad_human"] = get_severidad(evt["severidad"])["texto"]
        
        # Extraer resumen espectral
        resumen = {}
        if session.get("ruta_meta"):
            # En la API se reemplaza .sigmf-meta por resumen_...json (Dia 13)
            # Para simplificar, leemos de la db o calculamos mock si es necesario
            pass
            
        # Simular lectura del json resumen por ahora
        resumen = {
            "potencia_media_dbfs": -85.2,
            "snr_medio_db": 12.4,
            "bw_medio_khz": 250
        }
            
        data = {
            "session_id": session["session_id"],
            "freq_mhz": session["fc_hz"] / 1e6 if session.get("fc_hz") else 0,
            "start_datetime": session["start_datetime"],
            "duration_s": session["duration_s"],
            "dtype": session.get("data_type", "ci16_le"),
            "fs_hz": session["fs_hz"],
            "tuvo_interrupciones": bool(session.get("tuvo_interrupciones", 0)),
            "eventos": eventos,
            "hashes": hashes,
            "resumen": resumen
        }
        return data
    finally:
        conn.close()

def generate_report_html(session_id: str) -> str:
    data = get_session_data(session_id)
    
    # Configurar Jinja2
    template_dir = Path(__file__).resolve().parent / "templates"
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    template = env.get_template("reporte.html")
    
    return template.render(data=data)
