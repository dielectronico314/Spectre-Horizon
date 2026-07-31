#!/bin/bash
# scripts/probe.sh
# Script envoltorio para ejecutar la detección Python dentro de RF-Swift 
# y obtener exclusivamente el JSON limpio, omitiendo logs de depuración.

# Verificamos si el contenedor harogic_final está en ejecución
if ! docker ps | grep -q "harogic_final"; then
    echo '{"status": "error", "message": "El contenedor harogic_final no está en ejecución. Usa rfswift exec -c harogic_final"}'
    exit 1
fi

# Ejecutamos el script Python inyectándolo al contenedor, 
# y mandamos los logs (stderr) a /dev/null para que la salida estándar solo tenga el JSON.
docker exec -i harogic_final python3 < "$(dirname "$0")/probe_device.py" 2>/dev/null
