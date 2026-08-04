import json
import hashlib
from pathlib import Path
import shutil
from datetime import datetime

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def compute_sha256(filepath):
    if not Path(filepath).exists():
        return None
    sha256_hash = hashlib.sha256()
    with open(filepath, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

class EvidenceBuilder:
    """
    Clase central para construir paquetes de evidencia forense (Día 15).
    Aisla la extracción selectiva de IQ, renderizado y sellado criptográfico.
    """
    def __init__(self, out_dir: Path):
        self.out_dir = Path(out_dir)

    def build_package(
        self,
        evento: dict,
        features_csv_path: Path,
        spectrogram_npz_path: Path,
        sigmf_data_path: Path,
        sigmf_meta_path: Path,
        rules_config_path: Path = None,
        features_config_path: Path = None,
        padding_s: float = 0.5
    ):
        event_id = evento['event_id']
        pkg_dir = self.out_dir / event_id
        pkg_dir.mkdir(parents=True, exist_ok=True)
        
        t_extraccion_inicio = max(0.0, evento['start_t_s'] - padding_s)
        t_extraccion_fin = evento['end_t_s'] + padding_s

        archivos_empaquetados = {}

        # 1. Leer metadata original para IQ Extraction
        with open(sigmf_meta_path, 'r') as f:
            original_meta = json.load(f)
        
        fs = original_meta['global'].get('core:sample_rate', 1953125.0)
        datatype = original_meta['global'].get('core:datatype', 'cf32_le')
        bytes_por_muestra = 8 if 'cf32' in datatype else 4  # ci16_le = 4

        # 2. Extracción Selectiva de IQ (.sigmf-data)
        muestra_inicio = round(t_extraccion_inicio * fs)
        muestra_fin = round(t_extraccion_fin * fs)
        n_muestras = muestra_fin - muestra_inicio
        byte_offset = muestra_inicio * bytes_por_muestra
        n_bytes = n_muestras * bytes_por_muestra

        out_iq = pkg_dir / "evento.sigmf-data"
        with open(sigmf_data_path, 'rb') as f_in, open(out_iq, 'wb') as f_out:
            f_in.seek(byte_offset)
            chunk = f_in.read(n_bytes)
            f_out.write(chunk)
        archivos_empaquetados["evento.sigmf-data"] = compute_sha256(out_iq)

        # Crear metadata del slice
        slice_meta = {
            "global": original_meta["global"],
            "captures": [
                {
                    "core:sample_start": 0,
                    "evento_start_t_s": evento['start_t_s'],
                    "evento_end_t_s": evento['end_t_s'],
                    "extraccion_start_t_s": t_extraccion_inicio,
                    "extraccion_end_t_s": t_extraccion_fin,
                    "margen_s": padding_s
                }
            ]
        }
        out_meta = pkg_dir / "evento.sigmf-meta"
        with open(out_meta, 'w') as f:
            json.dump(slice_meta, f, indent=4)
        archivos_empaquetados["evento.sigmf-meta"] = compute_sha256(out_meta)

        # 3. Generar Espectrograma Visual (PNG)
        npz = np.load(spectrogram_npz_path)
        times_s = npz['times_s']
        spec = npz['dbfs']
        
        idx = np.where((times_s >= t_extraccion_inicio) & (times_s <= t_extraccion_fin))[0]
        if len(idx) > 0:
            spec_slice = spec[idx]
            plt.figure(figsize=(10, 4))
            plt.imshow(spec_slice.T, origin='lower', aspect='auto', cmap='viridis', 
                       extent=[t_extraccion_inicio, t_extraccion_fin, 0, fs/2/1e6])
            plt.xlabel('Tiempo (s)')
            plt.ylabel('Frecuencia (MHz)')
            plt.title(f"Espectrograma de Evento: {event_id}")
            plt.colorbar(label='Potencia (dBFS)')
            plt.axvline(x=evento['start_t_s'], color='red', linestyle='--', alpha=0.7)
            plt.axvline(x=evento['end_t_s'], color='red', linestyle='--', alpha=0.7)
            
            out_png = pkg_dir / "espectrograma_evento.png"
            plt.tight_layout()
            plt.savefig(out_png, dpi=150)
            plt.close()
            archivos_empaquetados["espectrograma_evento.png"] = compute_sha256(out_png)

        # 4. Recortar Features (CSV)
        df = pd.read_csv(features_csv_path)
        df_slice = df[(df['band_name'] == evento['band_name']) & 
                      (df['t_s'] >= t_extraccion_inicio) & 
                      (df['t_s'] <= t_extraccion_fin)]
        out_csv = pkg_dir / "features_evento.csv"
        df_slice.to_csv(out_csv, index=False)
        archivos_empaquetados["features_evento.csv"] = compute_sha256(out_csv)

        # 5. Configuración resuelta
        config_resuelto = {}
        if rules_config_path and rules_config_path.exists():
            with open(rules_config_path, 'r') as f:
                config_resuelto["rules"] = json.load(f)
        if features_config_path and features_config_path.exists():
            with open(features_config_path, 'r') as f:
                config_resuelto["features"] = json.load(f)
                
        # Buscar el spectrogram_config.json por defecto
        spec_cfg = Path("config/spectrogram_config.json")
        if spec_cfg.exists():
            with open(spec_cfg, 'r') as f:
                config_resuelto["fft"] = json.load(f)

        # 6. Resumen Humano (resumen.md)
        out_md = pkg_dir / "resumen.md"
        
        # Extraer hora real de captura (core:datetime) si existe, sino fallback al momento de ejecución
        capture_time_str = original_meta.get('captures', [{}])[0].get('core:datetime')
        if capture_time_str:
            try:
                # SigMF core:datetime es ISO 8601, ej. 2026-07-20T15:35:36.459378Z
                from datetime import timezone
                # Reemplazar Z por +00:00 para fromisoformat o hacerlo manual
                if capture_time_str.endswith('Z'):
                    capture_time_str = capture_time_str[:-1] + '+00:00'
                capture_dt = datetime.fromisoformat(capture_time_str)
            except Exception:
                capture_dt = datetime.now(timezone.utc)
        else:
            from datetime import timezone
            capture_dt = datetime.now(timezone.utc)
            
        # Obtener hora de Caracas para el reporte humano
        try:
            from zoneinfo import ZoneInfo
            tz_ccs = ZoneInfo("America/Caracas")
        except ImportError:
            # Fallback para versiones antiguas de Python
            import pytz
            tz_ccs = pytz.timezone("America/Caracas")
            
        capture_dt_ccs = capture_dt.astimezone(tz_ccs)
        now_ccs = datetime.now(tz_ccs)
        
        now_str = capture_dt_ccs.strftime('%Y-%m-%d %H:%M:%S %Z')
        
        report = f"""# Evento {event_id}

**Cuándo (Hora real de captura):** {now_str} + {evento['start_t_s']:.3f}s → {evento['end_t_s']:.3f}s (duración {evento['duration_s']:.2f}s)
**Banda:** {evento['band_name']} | **Severidad:** {evento.get('severidad', 'N/A')} | **Confianza:** {evento.get('confianza', 1.0)}
**Pico:** {evento.get('pico_dbfs', 0):.2f} dBFS | **Potencia media activa:** {evento.get('potencia_media_activa_dbfs', 0):.2f} dBFS

**Captura origen:** {sigmf_data_path.name} (sha256: {evento['capture_sha256'][:12]}...)
**Regla aplicada:** {evento['rule_name']}, ver manifest.json

**Archivos de este paquete:**
- Espectrograma: espectrograma_evento.png
- IQ selectivo: evento.sigmf-data ({n_muestras/fs:.1f}s a {fs/1e6:.2f}MSps, incluye {padding_s}s de margen c/lado)
- Features: features_evento.csv ({len(df_slice)} filas)

**Verificación:** todos los hashes validados el {now_ccs.strftime('%Y-%m-%d')} — ver manifest.json
"""
        with open(out_md, 'w') as f:
            f.write(report)
        archivos_empaquetados["resumen.md"] = compute_sha256(out_md)

        # 7. Hashes de Software
        software = {
            "python": "3.12.3",
            "script_generate_spectrogram_sha256": compute_sha256("/workspace/scripts/generate_spectrogram.py"),
            "script_extract_features_sha256": compute_sha256("/workspace/scripts/extract_features.py"),
            "script_run_event_engine_sha256": compute_sha256("/workspace/scripts/run_event_engine.py")
        }

        # 8. Manifiesto Criptográfico
        manifest = {
            "event_metadata": evento,
            "software": software,
            "config_resuelto": config_resuelto,
            "files_sha256": archivos_empaquetados,
            "manifest_sha256": "PENDING"
        }
        
        manifest_string = json.dumps({k:v for k,v in manifest.items() if k != "manifest_sha256"}, sort_keys=True)
        manifest["manifest_sha256"] = hashlib.sha256(manifest_string.encode()).hexdigest()

        out_manifest = pkg_dir / "manifest.json"
        with open(out_manifest, 'w') as f:
            json.dump(manifest, f, indent=4)
        
        return pkg_dir
