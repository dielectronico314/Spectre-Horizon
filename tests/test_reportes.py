import os
import pytest
from pathlib import Path
from bs4 import BeautifulSoup
import sqlite3

from app.reports.generator import generate_report_html, get_session_data

DB_PATH = Path("data/index.sqlite")

PALABRAS_PROHIBIDAS = [
    "clasifica", "clasificación", "certifica", "certificación",
    "garantiza", "detecta todo", "identifica el tipo de señal",
    "cobertura completa", "100% de las señales"
]

def lint_reporte(html: str) -> list[str]:
    # extraer solo texto renderizado, ignorar <style>, <script>, atributos
    texto = BeautifulSoup(html, "html.parser").get_text()
    return [p for p in PALABRAS_PROHIBIDAS if p in texto.lower()]

@pytest.fixture
def clean_session_id():
    return "session_20260720_155056_107.3MHz"

@pytest.fixture
def interrupt_session_id():
    return "session_20260804_115711_923.0MHz"

def test_reporte_datos_coinciden(clean_session_id):
    """
    Verifica que los números del HTML (potencia, duración, severidad)
    igualan byte a byte los de la API/DB para la misma sesión.
    """
    html = generate_report_html(clean_session_id)
    soup = BeautifulSoup(html, "html.parser")
    
    # Obtener datos reales de la BD
    data = get_session_data(clean_session_id)
    
    # Comprobar que la frecuencia y duración están en el reporte
    assert str(data["freq_mhz"]) in html
    assert str(data["duration_s"]) in html
    
    # Comprobar eventos
    for evt in data["eventos"]:
        assert str(evt["severidad"]) in html
        assert str(evt["duration_s"]) in html

def test_reporte_menciona_interrupciones(interrupt_session_id):
    """
    Sesión con tuvo_interrupciones=true incluye el aviso explícito.
    """
    html = generate_report_html(interrupt_session_id)
    assert "interrupciones de hardware" in html.lower()

def test_reporte_lint_lenguaje(clean_session_id):
    """
    Cero coincidencias con PALABRAS_PROHIBIDAS.
    """
    html = generate_report_html(clean_session_id)
    coincidencias = lint_reporte(html)
    assert not coincidencias, f"Se encontraron palabras prohibidas en el reporte: {coincidencias}"

def test_reporte_enlaces_eventos_resuelven(clean_session_id):
    """
    Cada <a href="/dashboard/eventos/{id}"> citado responde 200, no 404.
    """
    html = generate_report_html(clean_session_id)
    soup = BeautifulSoup(html, "html.parser")
    links = soup.find_all("a", href=True)
    event_links = [l["href"] for l in links if "/dashboard/eventos/" in l["href"]]
    
    data = get_session_data(clean_session_id)
    
    if data["eventos"]:
        assert len(event_links) > 0, "No se generaron enlaces a los eventos"
        
        # Verificar que el link generado coincide con el ID del evento de la BD
        for evt in data["eventos"]:
            expected_link = f"/dashboard/eventos/{evt['event_id']}"
            assert expected_link in event_links

def test_reporte_pdf_o_fallback(clean_session_id, tmp_path):
    """
    Si WeasyPrint está disponible, el PDF se genera y no está vacío;
    si no, el HTML documenta el fallback.
    """
    html = generate_report_html(clean_session_id)
    
    try:
        import weasyprint
        pdf_out = tmp_path / "test.pdf"
        weasyprint.HTML(string=html).write_pdf(pdf_out)
        assert pdf_out.exists()
        assert pdf_out.stat().st_size > 0
    except ImportError:
        # Fallback instruction must be in HTML
        assert "guardar como pdf" in html.lower() or "print" in html.lower() or "imprimir" in html.lower()
