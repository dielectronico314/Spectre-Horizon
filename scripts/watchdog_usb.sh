#!/bin/bash
# scripts/watchdog_usb.sh
# Monitorea el bus USB en el espacio de usuario (sin UDEV).
# Reinicia el contenedor si detecta que la antena fue desconectada y reconectada.

VENDOR_PRODUCT="367f:0001"
CONTAINER_NAME="mysdr"

echo "🛡️ Watchdog USB iniciado. Vigilando $VENDOR_PRODUCT..."

# Asumimos que inicialmente está conectado o queremos detectarlo al conectarlo
was_present=1
if ! lsusb -d "$VENDOR_PRODUCT" > /dev/null; then
    was_present=0
fi

while true; do
    if lsusb -d "$VENDOR_PRODUCT" > /dev/null; then
        if [ $was_present -eq 0 ]; then
            echo ""
            echo "⚡ [WATCHDOG] ¡Harogic reconectado! Reiniciando Docker para recuperar puertos USB..."
            docker restart "$CONTAINER_NAME" > /dev/null
            was_present=1
        fi
    else
        if [ $was_present -eq 1 ]; then
            echo ""
            echo "⚠️ [WATCHDOG] ¡Harogic desconectado físicamente!"
            was_present=0
        fi
    fi
    sleep 2
done
