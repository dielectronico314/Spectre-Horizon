#!/bin/bash
# scripts/probe.sh
# Script envoltorio para ejecutar la detección Python dentro de RF-Swift 
# y obtener exclusivamente el JSON limpio, omitiendo logs de depuración.

# Verificamos si el contenedor mysdr está en ejecución
if ! docker ps | grep -q "mysdr"; then
    echo '{"status": "error", "message": "El contenedor mysdr no está en ejecución. Usa rfswift exec -c mysdr"}'
    exit 1
fi

# Ejecutamos el script Python inyectándolo al contenedor, 
# y mandamos los logs (stderr) a /dev/null para que la salida estándar solo tenga el JSON.
docker exec -i mysdr python3 < "$(dirname "$0")/probe_device.py" 2>/dev/null
