#!/bin/bash
# Levanta API (8000) + Dashboard (8001) en paralelo

set -e

echo "🚀 Iniciando API en :8000 y Dashboard en :8001..."
echo ""

# API en background
echo "[API]  python -m uvicorn app.api.main:app --port 8000 --reload"
python -m uvicorn app.api.main:app --port 8000 --reload &
API_PID=$!

sleep 2

# Dashboard en otro terminal
echo "[DASH] python -m uvicorn app.dashboard.server:app --port 8001 --reload"
python -m uvicorn app.dashboard.server:app --port 8001 --reload &
DASH_PID=$!

echo ""
echo "✓ API       http://localhost:8000"
echo "✓ Dashboard http://localhost:8001"
echo "✓ Docs      http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers..."
echo ""

trap "kill $API_PID $DASH_PID 2>/dev/null; exit 0" INT TERM

wait
