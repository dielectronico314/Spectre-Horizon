#!/usr/bin/env python3
"""
generate_spectrogram.py — Espectrograma offline determinista desde IQ + SigMF.

Convención de escala (IMPORTANTE, leer antes de interpretar cualquier nivel):

    Se normaliza por S1 = sum(w[n])  (ganancia coherente de la ventana).

        P[k] = |FFT(x·w)[k]|^2 / S1^2
        dBFS = 10*log10(P[k])

    Con esta normalización:
      * Un tono CW complejo a fondo de escala y centrado en un bin lee 0.0 dBFS.
      * Un piso de ruido lee dBFS *por RBW*, donde RBW = ENBW_bins · fs/NFFT.
        => El nivel del piso NO tiene sentido sin declarar el RBW. Se emite en
           los metadatos y en el título del PNG.
      * Para pasar a dBFS/Hz (densidad):   dBFS_Hz = dBFS - 10*log10(RBW)

    No existe una normalización única correcta para tono y para ruido a la vez.
    Aquí se eligió la de analizador de espectro (normalizada a RBW), que es la
    que hace que el tono lea su potencia real. Está documentada y es la única
    aplicada; no se mezcla con 'density'.

Entrada real (no dBm): la salida es *relativa a fondo de escala* del ADC.
El paso a dBm es un offset constante que depende del reference level del
Harogic y del factor de escala a volts del paquete. Cuando ese dato se registre
en el .sigmf-meta, se suma como `cal_offset_db` (ver config) sin recalcular nada.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view

import matplotlib
matplotlib.use("Agg")  # headless: obligatorio antes de importar pyplot
import matplotlib.pyplot as plt
from scipy.signal import get_window
import scipy

# --------------------------------------------------------------------------- #
# SigMF: mapeo de core:datatype -> (dtype base, escala a fondo de escala)
# Solo tipos complejos: un espectrograma de IQ requiere FFT de dos lados.
# --------------------------------------------------------------------------- #
SIGMF_DTYPES: dict[str, tuple[np.dtype, float]] = {
    "ci8":     (np.dtype("i1"),   128.0),
    "ci8_le":  (np.dtype("i1"),   128.0),
    "ci16_le": (np.dtype("<i2"),  32768.0),
    "ci16_be": (np.dtype(">i2"),  32768.0),
    "ci32_le": (np.dtype("<i4"),  2147483648.0),
    "cf32_le": (np.dtype("<f4"),  1.0),
    "cf32_be": (np.dtype(">f4"),  1.0),
    "cf64_le": (np.dtype("<f8"),  1.0),
}


@dataclass(frozen=True)
class Params:
    nfft: int
    window: str              # nombre para scipy.signal.get_window
    window_arg: float | None # p.ej. beta de kaiser; None si no aplica
    overlap: float           # 0.0–0.95
    remove_dc: bool
    cal_offset_db: float
    max_seconds: float | None
    png_max_cols: int
    png_time_reduction: str  # "maxhold" | "mean"
    png_vmin_percentile: float
    png_vmax_percentile: float
    png_cmap: str
    png_dpi: int


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #
def sha256(path: Path, chunk: int = 1 << 22) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for blk in iter(lambda: f.read(chunk), b""):
            h.update(blk)
    return h.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def load_sigmf(meta_path: Path) -> tuple[dict, Path]:
    """Lee el .sigmf-meta y localiza el .sigmf-data (o .iq) hermano."""
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    stem = meta_path.name
    for suffix in (".sigmf-meta", ".meta", ".json"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    for cand in (f"{stem}.sigmf-data", f"{stem}.iq", f"{stem}.bin", f"{stem}.dat"):
        p = meta_path.with_name(cand)
        if p.exists():
            return meta, p
    raise FileNotFoundError(
        f"No encontré el archivo de datos junto a {meta_path.name} "
        f"(probé .sigmf-data/.iq/.bin/.dat)"
    )


def read_sigmf_fields(meta: dict) -> tuple[str, float, float, dict]:
    """Extrae datatype, sample_rate y frecuencia central. Nada hardcodeado."""
    g = meta.get("global", {})
    datatype = g.get("core:datatype")
    if datatype is None:
        raise ValueError("core:datatype ausente en global")
    if not datatype.startswith("c"):
        raise ValueError(
            f"core:datatype={datatype} es real. Este script asume IQ complejo "
            "(FFT de dos lados). Un archivo real requiere otra ruta."
        )

    fs = g.get("core:sample_rate")
    caps = meta.get("captures") or [{}]
    cap0 = caps[0]
    if fs is None:
        fs = cap0.get("core:sample_rate")
    if fs is None:
        raise ValueError("core:sample_rate ausente en global y en captures[0]")

    fc = cap0.get("core:frequency", g.get("core:frequency", 0.0))
    return datatype, float(fs), float(fc), g


def window_vector(p: Params) -> np.ndarray:
    """Ventana PERIÓDICA (fftbins=True). np.hanning es simétrica -> sesgo de fuga."""
    spec = p.window if p.window_arg is None else (p.window, p.window_arg)
    return get_window(spec, p.nfft, fftbins=True).astype(np.float64)


def window_metrics(w: np.ndarray) -> tuple[float, float, float]:
    """S1, S2 y ENBW en bins. ENBW = N·S2/S1^2 (Hann=1.5, rect=1.0, BH4≈2.0)."""
    s1 = float(w.sum())
    s2 = float((w * w).sum())
    enbw_bins = len(w) * s2 / (s1 * s1)
    return s1, s2, enbw_bins


# --------------------------------------------------------------------------- #
# Motor STFT
# --------------------------------------------------------------------------- #
def stft_dbfs(
    data_path: Path,
    datatype: str,
    fs: float,
    p: Params,
    batch_frames: int = 256,
) -> tuple[np.ndarray, np.ndarray, dict]:
    """
    Devuelve (dbfs[n_frames, nfft] float32, times_s[n_frames] float64, info).
    Ejes de frecuencia ya con fftshift aplicado (DC al centro).
    """
    base_dtype, fullscale = SIGMF_DTYPES[datatype]
    n_fft = p.nfft
    hop = int(round(n_fft * (1.0 - p.overlap)))
    if hop < 1:
        raise ValueError("overlap demasiado alto: hop < 1 muestra")

    mm = np.memmap(data_path, dtype=base_dtype, mode="r")
    n_samples = mm.size // 2
    if p.max_seconds is not None:
        n_samples = min(n_samples, int(p.max_seconds * fs))
    if n_samples < n_fft:
        raise ValueError(f"solo {n_samples} muestras; se requieren >= {n_fft}")

    n_frames = 1 + (n_samples - n_fft) // hop

    w = window_vector(p)
    s1, s2, enbw_bins = window_metrics(w)
    w32 = w.astype(np.float32)
    inv_s1_sq = np.float64(1.0 / (s1 * s1))
    scale = np.float32(1.0 / fullscale)

    out = np.empty((n_frames, n_fft), dtype=np.float32)

    for start in range(0, n_frames, batch_frames):
        b = min(batch_frames, n_frames - start)
        first = start * hop
        span = (b - 1) * hop + n_fft
        # Lectura contigua única del memmap -> float32 -> vista complex64.
        # (una sola pasada de memoria: conversión + escalado juntos)
        raw = np.asarray(mm[2 * first : 2 * (first + span)], dtype=np.float32)
        z = raw.view(np.complex64) * scale

        frames = sliding_window_view(z, n_fft)[::hop][:b]  # vista, sin copiar
        blk = frames * w32                                  # materializa aquí
        if p.remove_dc:
            blk -= blk.mean(axis=1, keepdims=True)          # por trama, tras ventana

        X = np.fft.fft(blk, axis=1)
        pwr = (X.real.astype(np.float64) ** 2 + X.imag.astype(np.float64) ** 2)
        pwr *= inv_s1_sq
        out[start : start + b] = np.fft.fftshift(pwr, axes=1).astype(np.float32)

    # dB una sola vez, al final. Piso a -300 dB para evitar log(0)/-inf.
    np.maximum(out, np.float32(1e-30), out=out)
    dbfs = (10.0 * np.log10(out, out=out)) + np.float32(p.cal_offset_db)

    times = (np.arange(n_frames, dtype=np.float64) * hop + n_fft / 2.0) / fs
    info = {
        "n_samples_used": int(n_samples),
        "n_frames": int(n_frames),
        "hop_samples": int(hop),
        "bin_spacing_hz": fs / n_fft,
        "enbw_bins": enbw_bins,
        "rbw_hz": enbw_bins * fs / n_fft,
        "frame_duration_s": n_fft / fs,
        "window_s1": s1,
        "window_s2": s2,
        "coherent_gain": s1 / n_fft,
        "scalloping_loss_db_worst": None,  # informativo; ver docs
    }
    return dbfs, times, info


def freq_axis(fs: float, n_fft: int, fc: float) -> np.ndarray:
    return fc + np.fft.fftshift(np.fft.fftfreq(n_fft, d=1.0 / fs))


# --------------------------------------------------------------------------- #
# Render
# --------------------------------------------------------------------------- #
def reduce_time(dbfs: np.ndarray, target_cols: int, mode: str) -> tuple[np.ndarray, int]:
    """
    Reduce tramas -> columnas de pixel SIN perder transitorios.
    matplotlib submuestrea por vecino más cercano: eso tira al piso el 50% de
    solapamiento que pagaste. maxhold conserva el pico dentro de cada grupo.
    """
    n = dbfs.shape[0]
    if n <= target_cols:
        return dbfs, 1
    group = int(np.ceil(n / target_cols))
    pad = (-n) % group
    if pad:
        fill = -np.inf if mode == "maxhold" else np.nan
        dbfs = np.concatenate(
            [dbfs, np.full((pad, dbfs.shape[1]), fill, dtype=dbfs.dtype)]
        )
    blocks = dbfs.reshape(-1, group, dbfs.shape[1])
    red = blocks.max(axis=1) if mode == "maxhold" else np.nanmean(blocks, axis=1)
    return red.astype(np.float32), group


def render_png(
    dbfs: np.ndarray,
    freqs: np.ndarray,
    times: np.ndarray,
    info: dict,
    p: Params,
    out_png: Path,
    title: str,
) -> dict:
    img, group = reduce_time(dbfs, p.png_max_cols, p.png_time_reduction)
    finite = img[np.isfinite(img)]
    vmin = float(np.percentile(finite, p.png_vmin_percentile))
    vmax = float(np.percentile(finite, p.png_vmax_percentile))
    if vmax - vmin < 6.0:
        vmax = vmin + 6.0

    fig, ax = plt.subplots(figsize=(12, 7), dpi=p.png_dpi)
    im = ax.imshow(
        img.T,                       # (freq, time)
        origin="lower",
        aspect="auto",
        interpolation="nearest",     # sin suavizado: cada pixel es dato
        extent=[times[0], times[-1], freqs[0] / 1e6, freqs[-1] / 1e6],
        vmin=vmin,
        vmax=vmax,
        cmap=p.png_cmap,
    )
    ax.set_xlabel("Tiempo [s]")
    ax.set_ylabel("Frecuencia [MHz]")
    ax.set_title(
        f"{title}\n"
        f"NFFT={p.nfft}  ventana={p.window}  overlap={p.overlap:.0%}  "
        f"RBW={info['rbw_hz'] / 1e3:.3f} kHz  "
        f"Δt={info['frame_duration_s'] * 1e6:.2f} µs  "
        f"reducción t={group}× ({p.png_time_reduction})",
        fontsize=9,
    )
    cb = fig.colorbar(im, ax=ax, pad=0.01)
    cb.set_label(f"dBFS por RBW ({info['rbw_hz'] / 1e3:.3f} kHz)")
    fig.tight_layout()
    # metadata=None en los campos volátiles: sin timestamp -> PNG comparable
    fig.savefig(out_png, metadata={"Software": None, "Creation Time": None})
    plt.close(fig)
    return {"png_time_group": group, "png_vmin_db": vmin, "png_vmax_db": vmax}


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("meta", type=Path, help="ruta al .sigmf-meta")
    ap.add_argument("-c", "--config", type=Path,
                    default=Path("config/spectrogram_config.json"))
    ap.add_argument("-o", "--outdir", type=Path, default=Path("out"))
    ap.add_argument("--no-npz", action="store_true",
                    help="omite la matriz .npz (solo PNG)")
    args = ap.parse_args(argv)

    cfg_bytes = args.config.read_bytes()
    cfg = json.loads(cfg_bytes)
    fft_cfg, out_cfg = cfg["fft"], cfg["output"]
    p = Params(
        nfft=int(fft_cfg["nfft"]),
        window=str(fft_cfg["window"]),
        window_arg=fft_cfg.get("window_arg"),
        overlap=float(fft_cfg["overlap"]),
        remove_dc=bool(fft_cfg.get("remove_dc", False)),
        cal_offset_db=float(cfg.get("calibration", {}).get("cal_offset_db", 0.0)),
        max_seconds=fft_cfg.get("max_seconds"),
        png_max_cols=int(out_cfg["png_max_cols"]),
        png_time_reduction=str(out_cfg["png_time_reduction"]),
        png_vmin_percentile=float(out_cfg["png_vmin_percentile"]),
        png_vmax_percentile=float(out_cfg["png_vmax_percentile"]),
        png_cmap=str(out_cfg["png_cmap"]),
        png_dpi=int(out_cfg["png_dpi"]),
    )
    if p.nfft & (p.nfft - 1):
        print(f"[!] nfft={p.nfft} no es potencia de 2 (más lento, no incorrecto)",
              file=sys.stderr)

    meta, data_path = load_sigmf(args.meta)
    datatype, fs, fc, _ = read_sigmf_fields(meta)
    if datatype not in SIGMF_DTYPES:
        raise ValueError(f"core:datatype no soportado: {datatype}")

    args.outdir.mkdir(parents=True, exist_ok=True)
    stem = data_path.stem

    dbfs, times, info = stft_dbfs(data_path, datatype, fs, p)
    freqs = freq_axis(fs, p.nfft, fc)

    print(f"  fs={fs / 1e6:.6f} MSa/s  fc={fc / 1e6:.6f} MHz  datatype={datatype}")
    print(f"  tramas={info['n_frames']}  Δf={info['bin_spacing_hz'] / 1e3:.3f} kHz  "
          f"RBW={info['rbw_hz'] / 1e3:.3f} kHz  Δt={info['frame_duration_s'] * 1e6:.3f} µs")
    print(f"  matriz {dbfs.shape} float32 = {dbfs.nbytes / 2**20:.1f} MiB")

    out_png = args.outdir / f"{stem}_espectrograma.png"
    render_info = render_png(dbfs, freqs, times, info, p, out_png,
                            title=f"{stem} — {data_path.name}")

    manifest = {
        "input": {
            "meta_file": args.meta.name,
            "data_file": data_path.name,
            "data_sha256": sha256(data_path),
            "datatype": datatype,
            "sample_rate_hz": fs,
            "center_freq_hz": fc,
        },
        "config": {"file": args.config.name, "sha256": sha256_bytes(cfg_bytes),
                   "resolved": asdict(p)},
        "derived": info | render_info,
        "scale": {
            "unit": "dBFS por RBW",
            "normalization": "|FFT(x*w)|^2 / (sum(w))^2",
            "fullscale_divisor": SIGMF_DTYPES[datatype][1],
            "cw_fullscale_on_bin_reads_db": 0.0,
            "to_dbfs_per_hz": "dBFS - 10*log10(rbw_hz)",
        },
        # Reproducibilidad VERIFICABLE, no asumida: la FFT en punto flotante no
        # es bit-exacta entre versiones/CPUs. Se registra el entorno y se
        # comparan hashes.
        "environment": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "matplotlib": matplotlib.__version__,
            "machine": platform.machine(),
            "platform": platform.platform(),
        },
    }

    if not args.no_npz:
        out_npz = args.outdir / f"{stem}_espectrograma.npz"
        np.savez(  # sin comprimir: float32 ~incompresible, comprimir solo cuesta
            out_npz,
            dbfs=dbfs,
            freqs_hz=freqs,
            times_s=times,
            manifest_json=np.array(json.dumps(manifest, indent=2)),
        )
        manifest["derived"]["npz_sha256"] = sha256(out_npz)
        print(f"  -> {out_npz}")

    # --------------------------------------------------------------------------- #
    # Generación de matriz 3D decimada para Plotly.js (WebGL en el navegador)
    # Target: ~250x200 puntos. Max-hold en tiempo, promedio lineal en frecuencia.
    # --------------------------------------------------------------------------- #
    TARGET_T = 250
    TARGET_F = 200
    
    t_factor = max(1, dbfs.shape[0] // TARGET_T)
    f_factor = max(1, dbfs.shape[1] // TARGET_F)
    
    t_len = (dbfs.shape[0] // t_factor) * t_factor
    f_len = (dbfs.shape[1] // f_factor) * f_factor
    
    # Max-hold en tiempo
    dbfs_t = dbfs[:t_len, :].reshape(-1, t_factor, dbfs.shape[1]).max(axis=1)
    times_dec = times[:t_len:t_factor]
    
    # Promedio en potencia lineal en frecuencia
    linear_power = 10 ** (dbfs_t[:, :f_len] / 10.0)
    linear_dec = linear_power.reshape(dbfs_t.shape[0], -1, f_factor).mean(axis=2)
    
    # Evitar log10(0)
    dbfs_dec = 10 * np.log10(np.clip(linear_dec, 1e-12, None))
    
    # Para freqs_dec, promedio del bin
    freqs_dec = freqs[:f_len].reshape(-1, f_factor).mean(axis=1)
    
    out_3d_json = args.outdir / f"{stem}_waterfall3d.json"
    with open(out_3d_json, 'w') as f3d:
        json.dump({
            "times_s": np.round(times_dec, 3).tolist(),
            "freqs_hz": np.round(freqs_dec, 1).tolist(),
            "dbfs": np.round(dbfs_dec, 2).tolist()
        }, f3d, separators=(',', ':'))
        
    manifest["derived"]["waterfall3d_sha256"] = sha256(out_3d_json)
    print(f"  -> {out_3d_json} (decimado t={t_factor}x, f={f_factor}x)")

    manifest["derived"]["png_sha256"] = sha256(out_png)
    out_man = args.outdir / f"{stem}_manifest.json"
    out_man.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"  -> {out_png}\n  -> {out_man}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
