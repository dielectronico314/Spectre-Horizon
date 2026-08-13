import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import sqlite3

import sys
sys.path.append(str(Path(__file__).parent.parent))
from app.api.main import app
from app.api.db import DB_PATH

client = TestClient(app)

def test_health_ok():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_sessions_list_filtro_fecha():
    # 1. Caso Positivo (Julio): La sesión del 20 de Julio de 2026 entra en el rango.
    res_in = client.get("/api/v1/sessions?desde=2026-07-01&hasta=2026-07-31")
    assert res_in.status_code == 200
    assert len(res_in.json()) >= 1
    
    # 2. Caso Negativo (Agosto 2030): Rango futuro donde no hay sesiones. 
    res_out = client.get("/api/v1/sessions?desde=2030-08-01&hasta=2030-08-15")
    assert res_out.status_code == 200
    assert len(res_out.json()) == 0  # <--- Falla si la API ignora el filtro

def test_events_filtro_severidad_invalida():
    response = client.get("/api/v1/events?severidad=critical")
    assert response.status_code == 422
    # Update expected detail since custom HTTPException handler was added
    assert "error" in response.json()
    assert "severidad debe ser" in response.json()["error"]["message"]

def test_evento_detalle_404():
    response = client.get("/api/v1/events/este_id_no_existe_jamaz")
    assert response.status_code == 404

def test_evidence_path_traversal():
    # Obtenemos un event_id valido primero
    res_events = client.get("/api/v1/events")
    assert res_events.status_code == 200
    events = res_events.json()
    if not events:
        pytest.skip("No hay eventos en la BD para probar path traversal")
    
    event_id = events[0]["event_id"]
    
    # Intento de path traversal clásico (URL-encoded para que llegue al parámetro filename en FastAPI)
    response = client.get(f"/api/v1/events/{event_id}/evidence/..%2F..%2F..%2Fetc%2Fpasswd")
    assert response.status_code == 404
    assert "Archivo no permitido" in response.json()["error"]["message"]

def test_navegacion_completa():
    """
    test_navegacion_completa:
    El que prueba el criterio oficial: GET /sessions/{id} -> 
    tomar un event_id -> GET /events/{event_id} -> 
    tomar link de evidencia -> GET ese link -> confirmar 200.
    """
    # 1. Traer lista de sesiones (para conocer un session_id valido)
    res_sessions = client.get("/api/v1/sessions")
    assert res_sessions.status_code == 200
    sessions = res_sessions.json()
    if not sessions:
        pytest.skip("No hay sesiones en la BD para probar navegación")
    session_id = sessions[0]["session_id"]
    
    # 2. Consultar la sesión específica
    res_sess = client.get(f"/api/v1/sessions/{session_id}")
    assert res_sess.status_code == 200
    sess_data = res_sess.json()
    
    eventos = sess_data.get("eventos", [])
    assert len(eventos) > 0
    event_id = eventos[0]
    
    # 3. Consultar el evento específico
    res_evt = client.get(f"/api/v1/events/{event_id}")
    assert res_evt.status_code == 200
    
    # 4. Obtener links de evidencia
    res_evd = client.get(f"/api/v1/events/{event_id}/evidence")
    assert res_evd.status_code == 200
    evd_data = res_evd.json()
    
    archivos = evd_data.get("archivos", {})
    manifest_link = archivos.get("manifest")
    assert manifest_link is not None
    
    # 5. Descargar archivo específico (El link devuelto es ej: /api/v1/events/{id}/evidence/manifest.json)
    res_file = client.get(manifest_link)
    
    assert res_file.status_code == 200
    assert len(res_file.content) > 0                   # <--- Valida que no viene vacío
    assert b"event_metadata" in res_file.content       # <--- Valida el contenido real
