#!/bin/bash
# scripts/capture.sh
# Wrapper para lanzar la captura parametrizada dentro de RF-Swift

echo "Lanzando script de captura en el contenedor RF-Swift..."
# Inyectamos el script de Python vía stdin y le pasamos los argumentos ($@)
docker exec -i mysdr python3 - "$@" < "$(dirname "$0")/capture_iq.py"

echo -e "\nSincronizando archivos capturados a tu escritorio..."
mkdir -p rf-spectrum/data/samples
docker cp mysdr:/workspace/rf-spectrum/data/samples/. rf-spectrum/data/samples/
echo "¡Sincronización completada!"
