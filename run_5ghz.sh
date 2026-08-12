#!/bin/bash
set -e
SESSION_DIR="rf-spectrum/data/samples/test_5GHz"
META_FILE="$SESSION_DIR/test_5GHz.sigmf-meta"
docker exec -w /workspace harogic_final python3 scripts/generate_spectrogram.py "$META_FILE" -o "$SESSION_DIR"
NPZ_FILE=$(ls $SESSION_DIR/*_espectrograma.npz | head -1)
docker exec -w /workspace harogic_final python3 scripts/extract_features.py "$NPZ_FILE" --out-dir "$SESSION_DIR"
CSV_FILE=$(ls $SESSION_DIR/features_*.csv | head -1)
docker exec -w /workspace harogic_final python3 scripts/run_event_engine.py "$CSV_FILE" --out-dir "$SESSION_DIR"
JSON_FILE=$(ls $SESSION_DIR/eventos_*.json | head -1)
docker exec -w /workspace harogic_final python3 scripts/batch_evidence_builder.py "$JSON_FILE" "$SESSION_DIR"
