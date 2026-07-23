#!/bin/bash
# scripts/validate.sh
# Wrapper para auditar metadatos SigMF dentro del contenedor Docker

echo "Instalando jsonschema en el contenedor..."
docker exec mysdr pip install --quiet jsonschema --break-system-packages

echo "Copiando esquema de validación al contenedor..."
docker exec mysdr mkdir -p /workspace/rf-spectrum/schema
docker cp rf-spectrum/schema/sigmf_v0.1.schema.json mysdr:/workspace/rf-spectrum/schema/

echo "Ejecutando auditoría de contratos SigMF sobre las muestras..."
docker exec -i mysdr python3 - "$@" < "$(dirname "$0")/validate_meta.py"
