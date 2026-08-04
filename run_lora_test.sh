#!/bin/bash
set -e
# Script para correr la prueba completa de LoRa 923MHz (Día 1 a 16) desde el HOST

echo "=========================================================="
echo "Iniciando prueba integral de LoRa (923 MHz) por 3 minutos"
echo "=========================================================="

# 1. Ejecutar captura dentro de Docker
docker exec -w /workspace harogic_final python3 scripts/capture_iq.py --freq 923e6 --rate 1.95e6 --duration 180 --gain 40 --outdir rf-spectrum/data/samples

# 2. Localizar la sesión generada (en el host)
SESSION_DIR=$(ls -td rf-spectrum/data/samples/session_* | head -1)
META_FILE=$(ls $SESSION_DIR/*.sigmf-meta | head -1)

echo "----------------------------------------"
echo "Procesando sesión: $SESSION_DIR"
echo "----------------------------------------"

# 3. Espectrograma (Día 10)
docker exec -w /workspace harogic_final python3 scripts/generate_spectrogram.py "$META_FILE" -o "$SESSION_DIR"

# 4. Extracción de Features (Día 13)
NPZ_FILE=$(ls $SESSION_DIR/*_espectrograma.npz | head -1)
docker exec -w /workspace harogic_final python3 scripts/extract_features.py "$NPZ_FILE" --out-dir "$SESSION_DIR"

# 5. Motor de Eventos (Día 14)
CSV_FILE=$(ls $SESSION_DIR/features_*.csv | head -1)
docker exec -w /workspace harogic_final python3 scripts/run_event_engine.py "$CSV_FILE" --out-dir "$SESSION_DIR"

# 6. Evidencia Forense (Día 15)
JSON_FILE=$(ls $SESSION_DIR/eventos_*.json | head -1)
docker exec -w /workspace harogic_final python3 scripts/batch_evidence_builder.py "$JSON_FILE" "$SESSION_DIR"

# 7. Indexación BD (Día 16)
docker exec -w /workspace harogic_final python3 scripts/build_index.py

echo "=========================================================="
echo "¡Prueba finalizada! Puedes revisar la BD o la API."
echo "=========================================================="
