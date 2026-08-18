#!/bin/bash
set -e

echo "Iniciando servicios de Harogic (Docker)..."

if pgrep -f "uvicorn app.api.main:app" > /dev/null; then
  echo "La API ya se encuentra corriendo. No se reinicia."
else
  echo "Levantando API y Dashboard..."
  PYTHONPATH=/workspace python3 -m uvicorn app.api.main:app --host 0.0.0.0 --port 8000 &
fi

echo "Servicios activos."
