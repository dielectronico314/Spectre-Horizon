#!/bin/bash
# Script para desinstalar la regla UDEV del Harogic SDR
# IMPORTANTE: Este script debe ser ejecutado como superusuario (sudo)

if [ "$EUID" -ne 0 ]; then
  echo "❌ Error: Por favor, ejecuta este script con permisos de administrador (sudo)."
  echo "Comando: sudo bash $0"
  exit 1
fi

echo "================================================="
echo " Desinstalando regla udev para Harogic SDR       "
echo "================================================="

RULE_FILE="/etc/udev/rules.d/99-harogic-docker.rules"

if [ -f "$RULE_FILE" ]; then
    echo "🗑️ Eliminando $RULE_FILE..."
    rm "$RULE_FILE"
    
    echo "🔄 Recargando reglas del kernel (udevadm)..."
    udevadm control --reload-rules
    udevadm trigger
    
    echo "✅ ¡Desinstalación exitosa! Tu sistema está libre de la regla UDEV."
else
    echo "⚠️ La regla no existe en el sistema. No hay nada que desinstalar."
fi
