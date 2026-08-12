#!/bin/bash
set -e

echo "Preparando Entorno Harogic (Docker)..."

# Verificar si el contenedor está encendido, si no, prenderlo
if [ "$(docker inspect -f '{{.State.Running}}' harogic_final 2>/dev/null)" != "true" ]; then
    echo "El contenedor estaba apagado. Encendiéndolo..."
    docker start harogic_final
    sleep 2 # Darle un par de segundos al contenedor para levantar su red interna
fi

docker exec -d harogic_final bash -c "/workspace/scripts/start_services.sh > /workspace/services.log 2>&1"

echo "Esperando a que la API levante..."
sleep 2

if curl -sf http://localhost:8000/api/v1/health > /dev/null; then
  echo "Sistema Harogic listo. Abre http://localhost:8000"
else
  echo "⚠ Algo falló — revisa: docker exec harogic_final cat /workspace/services.log"
  exit 1
fi
