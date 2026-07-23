#!/bin/bash
# Script de instalación de UDEV para USB Hotplugging de Harogic SDR
# IMPORTANTE: Este script debe ser ejecutado como superusuario (sudo)

if [ "$EUID" -ne 0 ]; then
  echo "❌ Error: Por favor, ejecuta este script con permisos de administrador (sudo)."
  echo "Comando: sudo bash $0"
  exit 1
fi

echo "================================================="
echo " Instalando regla udev para Harogic SDR (Docker) "
echo "================================================="

# Variables
RULE_FILE="scripts/99-harogic-docker.rules"
DEST_DIR="/etc/udev/rules.d/"

# 1. Verificar que la regla exista localmente
if [ ! -f "$RULE_FILE" ]; then
    echo "❌ Error: No se encontró el archivo $RULE_FILE"
    exit 1
fi

# 2. Copiar la regla a udev
echo "📄 Copiando regla a $DEST_DIR..."
cp $RULE_FILE $DEST_DIR

# 3. Recargar reglas
echo "🔄 Recargando reglas del kernel (udevadm)..."
udevadm control --reload-rules
udevadm trigger

echo "✅ ¡Instalación exitosa!"
echo "Ahora, cada vez que conectes la antena Harogic, el contenedor 'mysdr' se reiniciará automáticamente."
