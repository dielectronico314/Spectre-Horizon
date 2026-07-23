#!/bin/bash
# scripts/capture.sh
# Wrapper para lanzar la captura parametrizada dentro de RF-Swift y vigilar USB

echo "Iniciando sistema de captura..."

# 1. Iniciar watchdog en background y guardar su PID
./scripts/watchdog_usb.sh &
WATCHDOG_PID=$!

# Asegurar que si el usuario presiona Ctrl+C, matamos al watchdog también
trap "echo -e '\n🛑 Cancelando sesión...'; kill $WATCHDOG_PID 2>/dev/null; exit" INT TERM

FREQ=""
RATE=""
GAIN="0"
DURATION="60"
CHUNK="60"
ANTENNA="Dipolo_Bigotes"
LOCATION="Laboratorio_Local"

# 3. Parsear argumentos
while [[ "$#" -gt 0 ]]; do
    case $1 in
        --freq) FREQ="$2"; shift ;;
        --rate) RATE="$2"; shift ;;
        --gain) GAIN="$2"; shift ;;
        --duration) DURATION="$2"; shift ;;
        --chunk-duration) CHUNK="$2"; shift ;;
        --antenna) ANTENNA="$2"; shift ;;
        --location) LOCATION="$2"; shift ;;
        *) echo "Parámetro desconocido: $1"; exit 1 ;;
    esac
    shift
done

echo "Instalando dependencias de telemetría (psutil)..."
docker exec mysdr pip install --quiet psutil

echo "Lanzando script de captura en el contenedor RF-Swift..."
# Bucle infinito para soportar reinicios del contenedor
while true; do
    docker exec -i mysdr python3 - \
        --freq "$FREQ" \
        --rate "$RATE" \
        --gain "$GAIN" \
        --duration "$DURATION" \
        --chunk-duration "$CHUNK" \
        --antenna "$ANTENNA" \
        --location "$LOCATION" < "$(dirname "$0")/capture_iq.py"
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
