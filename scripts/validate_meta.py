#!/usr/bin/env python3
"""
validate_meta.py
Script para auditar y validar archivos .sigmf-meta contra nuestro Contrato JSON (v0.1).
"""

import os
import sys
import json
import argparse
try:
    import jsonschema
    from jsonschema import validate
except ImportError:
    print("❌ Error: Necesitas instalar jsonschema. Ejecuta: pip install jsonschema")
    sys.exit(1)

# Determinar rutas absolutas para el contenedor Docker
PROJECT_ROOT = "/workspace"
SCHEMA_PATH = os.path.join(PROJECT_ROOT, "rf-spectrum", "schema", "sigmf_v0.1.schema.json")
DEFAULT_SAMPLES_DIR = os.path.join(PROJECT_ROOT, "rf-spectrum", "data", "samples")

def load_schema(schema_path):
    if not os.path.exists(schema_path):
        print(f"❌ Error: El contrato no se encontró en {schema_path}")
        sys.exit(1)
    with open(schema_path, 'r') as f:
        return json.load(f)

def validate_file(filepath, schema):
    filename = os.path.basename(filepath)
    try:
        with open(filepath, 'r') as f:
            data = json.load(f)
        validate(instance=data, schema=schema)
        print(f"✅ {filename} : [PASS] Cumple el contrato.")
        return True
    except jsonschema.exceptions.ValidationError as err:
        print(f"❌ {filename} : [FAIL] Violación de Contrato!")
        print(f"   -> Detalle: {err.message}")
        return False
    except json.JSONDecodeError as err:
        print(f"❌ {filename} : [FAIL] JSON Corrupto!")
        print(f"   -> Detalle: {err.msg}")
        return False
    except Exception as e:
        print(f"❌ {filename} : [ERROR] {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Validador de Contrato de Metadatos (SigMF)")
    parser.add_argument("--path", type=str, default=DEFAULT_SAMPLES_DIR,
                        help="Ruta al archivo o directorio a validar")
    args = parser.parse_args()

    schema = load_schema(SCHEMA_PATH)
    print("==================================================")
    print(f" 🛡️  AUDITOR DE METADATOS (Contrato v0.1) ")
    print("==================================================")

    target = args.path
    if not os.path.exists(target):
        print(f"❌ Error: La ruta '{target}' no existe.")
        sys.exit(1)

    passed = 0
    failed = 0

    if os.path.isfile(target):
        if target.endswith('.sigmf-meta'):
            if validate_file(target, schema):
                passed += 1
            else:
                failed += 1
        else:
            print("El archivo no tiene extensión .sigmf-meta")
    elif os.path.isdir(target):
        # Escaneo recursivo
        for root, _, files in os.walk(target):
            for file in files:
                if file.endswith('.sigmf-meta'):
                    full_path = os.path.join(root, file)
                    if validate_file(full_path, schema):
                        passed += 1
                    else:
                        failed += 1

    print("==================================================")
    print(f" Total Analizados : {passed + failed}")
    print(f" Exitosos (PASS)  : {passed}")
    print(f" Fallidos (FAIL)  : {failed}")
    print("==================================================")
    
    if failed > 0:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
