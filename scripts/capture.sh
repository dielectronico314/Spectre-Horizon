#!/bin/bash
# scripts/capture.sh
# Wrapper para lanzar la captura parametrizada dentro de RF-Swift y vigilar USB

echo "Iniciando sistema de captura..."

# 1. Iniciar watchdog en background y guardar su PID
./scripts/watchdog_usb.sh &
WATCHDOG_PID=$!

# Asegurar que si el usuario presiona Ctrl+C, matamos al watchdog también
trap "echo -e '\n🛑 Cancelando sesión...'; kill $WATCHDOG_PID 2>/dev/null; exit" INT TERM

echo "Instalando dependencias de telemetría (psutil)..."
docker exec mysdr pip install --quiet psutil

echo "Lanzando script de captura en el contenedor RF-Swift..."
# Bucle infinito para soportar reinicios del contenedor
while true; do
    # Inyectamos el script de Python vía stdin y le pasamos los argumentos ($@)
    docker exec -i mysdr python3 - "$@" < "$(dirname "$0")/capture_iq.py"
    EXIT_CODE=$?
    
    # Si la salida es 0 (terminó el tiempo) o 130 (Ctrl+C), salimos limpio
    if [ $EXIT_CODE -eq 0 ] || [ $EXIT_CODE -eq 130 ]; then
        break
    fi
    
    # Si sale con error (ej. Docker lo mató porque se reinició), esperamos y volvemos a lanzar
    echo "⏳ Esperando a que el contenedor mysdr esté listo de nuevo..."
    sleep 3
done

# Limpieza
kill $WATCHDOG_PID 2>/dev/null

echo -e "\nSincronizando archivos capturados a tu escritorio..."
mkdir -p rf-spectrum/data/samples
docker cp mysdr:/workspace/rf-spectrum/data/samples/. rf-spectrum/data/samples/
echo "¡Sincronización completada!"
