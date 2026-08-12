#!/usr/bin/env python3
import sys
import argparse
from pathlib import Path

# Agregar ruta para imports
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.append(str(PROJECT_ROOT))

from app.reports.generator import generate_report_html

def main():
    parser = argparse.ArgumentParser(description="Generar Reporte Técnico de Sesión")
    parser.add_argument("session_id", help="El ID de la sesión a reportar")
    parser.add_argument("--out-dir", default="out", help="Directorio de salida (default: out/)")
    
    args = parser.parse_args()
    session_id = args.session_id
    
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        html_content = generate_report_html(session_id)
        
        # Guardar HTML
        html_path = out_dir / f"reporte_{session_id}.html"
        html_path.write_text(html_content, encoding="utf-8")
        print(f"✓ Reporte HTML generado: {html_path}")
        
        # Intentar PDF
        try:
            import weasyprint
            pdf_path = out_dir / f"reporte_{session_id}.pdf"
            weasyprint.HTML(string=html_content).write_pdf(pdf_path)
            print(f"✓ Reporte PDF generado: {pdf_path}")
        except ImportError:
            print("⚠ WeasyPrint no disponible — usa Ctrl+P > Guardar como PDF en el navegador para imprimir el HTML")
            
    except Exception as e:
        print(f"Error generando reporte: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
