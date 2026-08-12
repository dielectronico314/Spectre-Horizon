#!/bin/bash
set -e

echo "=========================================================="
echo "Iniciando Barrido Masivo de Sesiones Reales (Fase 1: Reprocesamiento)"
echo "=========================================================="

SAMPLES_DIR="/workspace/rf-spectrum/data/samples"

# 1. Reprocesar todas las sesiones
for dir in $SAMPLES_DIR/session_*/; do
    if [[ "$dir" == *"session_golden_demo_v1"* ]]; then
        continue
    fi
    
    session_id=$(basename "$dir")
    npz_file=$(ls "$dir"/*_espectrograma.npz 2>/dev/null | head -1 || true)
    
    if [ -f "$npz_file" ]; then
        echo "-> Reprocesando: $session_id"
        
        # Determinar el archivo de configuracion segun la frecuencia
        config_file="/workspace/config/features_config.json"
        if [[ "$session_id" == *"106.5MHz"* ]]; then
            config_file="/workspace/config/features_config_fm_106.5.json"
        fi
        
        python3 /workspace/scripts/extract_features.py "$npz_file" --config "$config_file" --out-dir "$dir" >/dev/null 2>&1
        
        csv_file="$dir/features_${session_id}.csv"
        
        if [ ! -f "$csv_file" ]; then
            echo "FALTA CSV: $session_id"
            continue
        fi
        
        if [ $(wc -l < "$csv_file") -gt 1 ]; then
            python3 /workspace/scripts/run_event_engine.py "$csv_file" --out-dir "$dir" >/dev/null 2>&1 || true
            json_file="$dir/eventos_${session_id}.json"
            if [ ! -f "$json_file" ]; then
                echo "FALTA JSON: $session_id"
                continue
            fi
            python3 /workspace/scripts/batch_evidence_builder.py "$json_file" "$dir" >/dev/null 2>&1 || true
        fi
    fi
done

# Tambien reprocesar el loose file de 106.5MHz
loose_npz="/workspace/rf-spectrum/data/samples/captura_106.5MHz_20260720_153534_espectrograma.npz"
if [ -f "$loose_npz" ]; then
    echo "-> Reprocesando archivo suelto: captura_106.5MHz_20260720_153534_espectrograma"
    python3 /workspace/scripts/extract_features.py "$loose_npz" --config "/workspace/config/features_config_fm_106.5.json" --out-dir "/workspace/rf-spectrum/data/samples" >/dev/null 2>&1
    loose_session_id="captura_106.5MHz_20260720_153534_espectrograma"
    csv_file="/workspace/rf-spectrum/data/samples/features_${loose_session_id}.csv"
    
    if [ ! -f "$csv_file" ]; then
        echo "FALTA CSV: $loose_session_id"
    elif [ $(wc -l < "$csv_file") -gt 1 ]; then
        python3 /workspace/scripts/run_event_engine.py "$csv_file" --out-dir "/workspace/rf-spectrum/data/samples" >/dev/null 2>&1 || true
        json_file="/workspace/rf-spectrum/data/samples/eventos_${loose_session_id}.json"
        if [ ! -f "$json_file" ]; then
            echo "FALTA JSON: $loose_session_id"
        else
            python3 /workspace/scripts/batch_evidence_builder.py "$json_file" "/workspace/rf-spectrum/data/samples" >/dev/null 2>&1 || true
        fi
    fi
fi


echo "=========================================================="
echo "Fase 2: Limpieza Quirurgica y Reindexacion"
echo "=========================================================="

rm -f /workspace/data/index.sqlite
python3 /workspace/scripts/build_index.py
python3 /workspace/check_orphans.py || true

echo "Barrido Finalizado."
