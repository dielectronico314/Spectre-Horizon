#!/bin/bash
set -e

echo "=========================================================="
echo "Generando Golden Dataset para Ensayo General (Día 19)"
echo "=========================================================="

SESSION_DIR="/workspace/rf-spectrum/data/samples/session_golden_demo_v1"
META_FILE="$SESSION_DIR/test_burst.sigmf-meta"

echo "1. Generando IQ Sintético..."
python3 /workspace/scripts/generate_synthetic_burst.py

echo "2. Generando Espectrograma..."
python3 /workspace/scripts/generate_spectrogram.py "$META_FILE" -o "$SESSION_DIR"

NPZ_FILE=$(ls $SESSION_DIR/*_espectrograma.npz | head -1)

echo "3. Extrayendo Features..."
python3 /workspace/scripts/extract_features.py "$NPZ_FILE" --out-dir "$SESSION_DIR"

CSV_FILE=$(ls $SESSION_DIR/features_*.csv | head -1)

echo "4. Detectando Eventos (Motor)..."
python3 /workspace/scripts/run_event_engine.py "$CSV_FILE" --out-dir "$SESSION_DIR"

JSON_FILE=$(ls $SESSION_DIR/eventos_*.json | head -1)

echo "5. Empaquetando Evidencia..."
python3 /workspace/scripts/batch_evidence_builder.py "$JSON_FILE" "$SESSION_DIR"

echo "6. Indexando Sesión en Base de Datos..."
python3 /workspace/scripts/build_index.py

echo "7. Verificando Idempotencia en BD..."
sqlite3 /workspace/data/index.sqlite "SELECT COUNT(*) FROM sessions WHERE session_id='session_golden_demo_v1';"

echo "=========================================================="
echo "Golden Dataset listo."
echo "=========================================================="
