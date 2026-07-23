#!/bin/bash
# scripts/replay.sh
# Wrapper para lanzar la reproducción offline dentro del contenedor Docker

if [ -z "$1" ]; then
    echo "Uso: $0 <ruta_al_archivo_sigmf-meta>"
    echo "Ejemplo: $0 rf-spectrum/data/samples/captura_106.5MHz_part001.sigmf-meta"
    exit 1
fi

META_PATH="$1"

# Verificar si la ruta es relativa y mapearla a la estructura interna del Docker
# Si el usuario pasó "rf-spectrum/data/samples/...", dentro del contenedor esto está en "/workspace/rf-spectrum/data/samples/..."
if [[ "$META_PATH" != /* ]]; then
    CONTAINER_PATH="/workspace/$META_PATH"
else
    CONTAINER_PATH="$META_PATH"
fi

echo "Iniciando Reproducción Offline (Día 9)..."

# Lanzar el script dentro del contenedor pasándolo por stdin para no tener que copiar el .py cada vez
docker exec -i mysdr python3 - --meta "$CONTAINER_PATH" < "$(dirname "$0")/replay_iq.py"
