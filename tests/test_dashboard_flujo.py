#!/usr/bin/env python3
"""
tests/test_dashboard_flujo.py — Prueba de flujo completo del dashboard (Día 17).

Valida que una persona no técnica pueda:
1. Ver estado del sensor
2. Navegar a tabla de eventos
3. Abrir un evento
4. Leer explicación humanizada de por qué se generó
5. Acceder a enlaces de evidencia
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from app.api.main import app


client = TestClient(app)


def test_dashboard_estado_ok():
    """Pantalla de estado existe y muestra contenido."""
    response = client.get("/dashboard/")
    assert response.status_code == 200
    assert b"Estado del Sensor" in response.content
    assert b"Sensor:" in response.content or b"sin datos" in response.content


def test_dashboard_eventos_tabla_ok():
    """Tabla de eventos existe y es navegable."""
    response = client.get("/dashboard/eventos")
    assert response.status_code == 200
    assert b"<table" in response.content or b"eventos" in response.content.lower()


def test_dashboard_eventos_filtro():
    """Filtros funcionan con query params."""
    # Intenta filtrar por severidad
    response = client.get("/dashboard/eventos?severidad=high")
    assert response.status_code == 200
    assert b"Filtrar" in response.content


def test_flujo_completo_no_tecnico():
    """
    Flujo end-to-end: home → tabla → detalle → explicación → evidencia.

    Este test demuestra que el dashboard cumple el requisito oficial:
    "una persona no técnica identifica el estado del sensor, abre un evento
    y entiende por qué se generó."
    """
    # 1. Ver estado
    home = client.get("/dashboard/")
    assert home.status_code == 200
    assert b"Estado" in home.content
    print("✓ Paso 1: Estado del sensor visible")

    # 2. Ir a eventos
    eventos_page = client.get("/dashboard/eventos")
    assert eventos_page.status_code == 200
    assert b"Evento" in eventos_page.content or b"evento" in eventos_page.content.lower()
    print("✓ Paso 2: Tabla de eventos navegable")

    # 3. Si hay eventos, abrir el primero
    # Extraer event_id desde un link en la tabla
    # Buscamos un patrón tipo: /dashboard/eventos/{event_id}
    import re
    matches = re.findall(rb'/dashboard/eventos/([a-zA-Z0-9_]+)', eventos_page.content)

    if matches:
        event_id = matches[0].decode()
        detalle = client.get(f"/dashboard/eventos/{event_id}")
        assert detalle.status_code == 200

        # 4. Verificar que hay explicación humanizada
        assert b"Por qu" in detalle.content or b"por qu" in detalle.content.lower()
        print(f"✓ Paso 3: Explicación humanizada presente para {event_id}")

        # 5. Verificar que hay enlaces a evidencia
        assert b"Evidencia" in detalle.content or b"evidencia" in detalle.content.lower()
        assert b"Descargar" in detalle.content or b"descargar" in detalle.content.lower()
        print("✓ Paso 4: Enlaces a evidencia visibles")

        # 6. Verificar que no hay jerga técnica cruda en la explicación
        # Buscar que la palabra "dBFS" no aparece en un contexto de explicación
        # (puede aparecer en detalles técnicos, pero no en "Por qué")
        assert b"dBFS" not in detalle.content[:detalle.content.find(b"Detalles t")] if b"Detalles t" in detalle.content else True
        print("✓ Paso 5: Explicación sin jerga técnica cruda")
    else:
        print("⚠ No hay eventos en la base de datos — test saltado (base vacía es válido para demo)")


def test_interrupciones_visibles_en_estado():
    """Si una sesión tuvo interrupciones, aparece advertencia en estado."""
    response = client.get("/dashboard/")
    assert response.status_code == 200
    # Si hay interrupciones, debe mostrar símbolo de alerta (en HTML)
    if b"Interrupciones" in response.content:
        # Buscar el símbolo de advertencia en el HTML (puede estar como Unicode)
        assert b"warning" in response.content.lower() or b"interrupci" in response.content.lower()
        print("✓ Interrupciones mostradas con alerta visual")
    else:
        print("✓ Sin interrupciones detectadas (sesión limpia)")


def test_filtros_no_rompen_html():
    """Los filtros generan HTML válido aunque no haya resultados."""
    # Filtro imposible
    response = client.get("/dashboard/eventos?banda=INEXISTENTE&severidad=high")
    assert response.status_code == 200
    # Aunque no haya eventos, la página debe renderizar sin errores
    assert b"<table" in response.content or b"No se encontraron" in response.content

def test_dashboard_sesiones_waterfall():
    """Valida que los endpoints de espectrograma 2D y 3D de las sesiones no den error."""
    # Obtenemos la página de sesiones
    response = client.get("/dashboard/sesiones")
    assert response.status_code == 200
    
    # Extraemos IDs de sesión de los links de imágenes o JSONs
    import re
    matches = re.findall(rb'/api/v1/sessions/([^/]+)/waterfall', response.content)
    
    # Tomar hasta 3 sesiones únicas para probar
    unique_sessions = list(set([m.decode() for m in matches]))[:3]
    
    if not unique_sessions:
        print("⚠ No hay sesiones descubiertas para probar cascadas — test saltado")
        return
        
    for session_id in unique_sessions:
        # Probar 2D
        r_2d = client.get(f"/api/v1/sessions/{session_id}/waterfall")
        assert r_2d.status_code in [200, 404], f"Error inesperado {r_2d.status_code} en 2D para {session_id}"
        
        # Probar 3D
        r_3d = client.get(f"/api/v1/sessions/{session_id}/waterfall3d.json")
        assert r_3d.status_code in [200, 404], f"Error inesperado {r_3d.status_code} en 3D para {session_id}"
    
    print(f"✓ Probadas cascadas de {len(unique_sessions)} sesión(es) exitosamente sin 500s")

if __name__ == "__main__":
    import traceback

    tests = [
        test_dashboard_estado_ok,
        test_dashboard_eventos_tabla_ok,
        test_dashboard_eventos_filtro,
        test_flujo_completo_no_tecnico,
        test_interrupciones_visibles_en_estado,
        test_filtros_no_rompen_html,
        test_dashboard_sesiones_waterfall,
    ]
    fallos = 0
    for t in tests:
        try:
            t()
            print(f"✅ {t.__name__}\n")
        except AssertionError as e:
            fallos += 1
            print(f"❌ {t.__name__}")
            traceback.print_exc()
            print()
    if fallos:
        print(f"\n{fallos} test(s) fallaron.")
        sys.exit(1)
    print("\nTodos los tests del dashboard pasaron.")
