#!/bin/bash
# scripts/test_sensor.sh
# Un test básico para confirmar que el contenedor y el sensor Harogic están funcionando.

echo "=========================================================="
echo "    INICIANDO TEST DEL SENSOR HAROGIC VIA RF-SWIFT        "
echo "=========================================================="
echo ""

# 1. Verificar si SAStudio4 está corriendo en el host, lo cual bloquea el sensor
if pgrep -x "SAStudio4" > /dev/null
then
    echo "❌ ERROR FATAL: El programa SAStudio4 se está ejecutando en la computadora principal (Host)."
    echo "Linux no permite compartir el SDR entre dos procesos al mismo tiempo."
    echo "Por favor, cierra SAStudio4 completamente antes de ejecutar este test."
    exit 1
fi

# 2. Ejecutar SoapySDRUtil dentro del contenedor para hacer un ping al hardware
echo "Consultando al contenedor 'mysdr' por dispositivos conectados..."
# Redirigimos stderr a stdout para poder leer los mensajes del contenedor
OUTPUT=$(rfswift exec -c mysdr --command "SoapySDRUtil --find" 2>&1)

# 3. Analizar la salida para determinar el estado
if echo "$OUTPUT" | grep -q "driver = harogic"; then
    echo ""
    echo "✅ ÉXITO: ¡El sensor Harogic fue detectado correctamente en el contenedor!"
    echo "----------------------------------------------------------"
    echo "$OUTPUT" | grep "label ="
    echo "$OUTPUT" | grep "serial ="
    echo "----------------------------------------------------------"
    echo "Todo el entorno está listo para correr capturas de espectro o usar GQRX."
    exit 0
else
    echo ""
    echo "❌ ERROR: No se detectó el sensor Harogic."
    echo "Diagnóstico rápido:"
    echo "  1. ¿El Harogic está conectado al puerto USB?"
    echo "  2. ¿Arrancaste el contenedor con permisos privilegiados (-u 1 y -s /dev/bus/usb)?"
    echo "  3. ¿Están los archivos de calibración (.cal) dentro de /usr/bin/CalFile/ en el contenedor?"
    echo ""
    echo "Salida del comando:"
    echo "$OUTPUT"
    exit 1
fi
