from pathlib import Path
from fastapi import HTTPException
from app.api.db import get_db_connection, DATA_ROOT

ALLOWED_FILES = {
    "manifest.json", 
    "resumen.md", 
    "espectrograma_evento.png",
    "evento.sigmf-data", 
    "evento.sigmf-meta", 
    "features_evento.csv"
}

def get_evidence_path(event_id: str, filename: str) -> Path:
    """
    Recupera y valida la ruta de un archivo de evidencia de forma segura,
    evitando vulnerabilidades de Path Traversal.
    """
    if filename not in ALLOWED_FILES:
        raise HTTPException(status_code=404, detail="Archivo no permitido o inexistente")
        
    conn = get_db_connection()
    try:
        row = conn.execute("SELECT ruta_evidencia FROM events WHERE event_id = ?", (event_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Evento no encontrado en la base de datos")
            
        # ruta_evidencia viene de la DB, por ejemplo "evidence/19c10fbb7b7e_FM_Sub1_0001"
        ruta_evidencia = row["ruta_evidencia"]
        
    finally:
        conn.close()

    base = Path(DATA_ROOT) / ruta_evidencia
    resolved = (base / filename).resolve()
    
    # Validar que la ruta resuelta siga estando dentro de DATA_ROOT (Cinturon y tirantes)
    if not resolved.is_relative_to(Path(DATA_ROOT).resolve()):
        raise HTTPException(status_code=403, detail="Acceso denegado")
        
    if not resolved.exists():
        raise HTTPException(status_code=404, detail="El archivo no existe físicamente en el servidor")
        
    return resolved
