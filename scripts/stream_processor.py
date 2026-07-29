#!/usr/bin/env python3
"""
stream_processor.py — Pipeline de Procesamiento Espectral Continuo (Streaming)

Implementa un Ring Buffer SPSC (Single-Producer Single-Consumer) con
multiprocessing.shared_memory para procesar capturas IQ en tiempo real.
- Hilo Productor: Adquiere datos (o hace replay de archivos).
- Hilo Consumidor: Procesa DSP (FFT, Escalado, Max-Hold) y reporta métricas.
"""

from __future__ import annotations

import argparse
import json
import time
import sys
import multiprocessing as mp
from multiprocessing import shared_memory
from pathlib import Path

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from scipy.signal import get_window

# --------------------------------------------------------------------------- #
# SigMF Datatypes
# --------------------------------------------------------------------------- #
SIGMF_DTYPES: dict[str, tuple[np.dtype, float]] = {
    "ci16_le": (np.dtype("<i2"),  32768.0),
    "cf32_le": (np.dtype("<f4"),  1.0),
}

# --------------------------------------------------------------------------- #
# Funciones DSP
# --------------------------------------------------------------------------- #
def window_vector(window_name: str, window_arg: float | None, nfft: int) -> np.ndarray:
    spec = window_name if window_arg is None else (window_name, window_arg)
    return get_window(spec, nfft, fftbins=True).astype(np.float64)

def window_metrics(w: np.ndarray) -> tuple[float, float, float]:
    s1 = float(w.sum())
    s2 = float((w * w).sum())
    enbw_bins = len(w) * s2 / (s1 * s1)
    return s1, s2, enbw_bins

# --------------------------------------------------------------------------- #
# Consumidor (DSP Processing)
# --------------------------------------------------------------------------- #
def consumer_process(
    shm_name: str,
    shape: tuple[int, int],
    dtype: np.dtype,
    head: mp.Value,
    tail: mp.Value,
    stop_flag: mp.Value,
    nfft: int,
    hop: int,
    window_name: str,
    window_arg: float | None,
    fullscale: float,
    cal_offset_db: float,
    remove_dc: bool
):
    shm = shared_memory.SharedMemory(name=shm_name)
    ring_buffer = np.ndarray(shape, dtype=dtype, buffer=shm.buf)
    capacity = shape[0]
    chunk_samples = shape[1] // 2  # IQ pairs

    w = window_vector(window_name, window_arg, nfft)
    s1, _, _ = window_metrics(w)
    w32 = w.astype(np.float32)
    inv_s1_sq = np.float64(1.0 / (s1 * s1))
    scale = np.float32(1.0 / fullscale)

    history_size = nfft - hop
    history = np.zeros(history_size, dtype=np.complex64)

    frames_processed = 0
    t_start = time.perf_counter()

    local_tail = tail.value

    try:
        while not stop_flag.value or local_tail < head.value:
            if local_tail < head.value:
                # Extraer chunk del ring buffer
                idx = local_tail % capacity
                raw = np.asarray(ring_buffer[idx], dtype=np.float32)
                z_chunk = raw.view(np.complex64) * scale

                # Cola de arrastre (Fronteras perfectas)
                z = np.concatenate((history, z_chunk))
                history = z[-history_size:] # Guardar para el siguiente lote

                # Crear ventanas deslizantes
                b = chunk_samples // hop
                frames = sliding_window_view(z, nfft)[::hop][:b]
                blk = frames * w32

                if remove_dc:
                    blk -= blk.mean(axis=1, keepdims=True)

                # FFT
                X = np.fft.fft(blk, axis=1)
                pwr = (X.real.astype(np.float64) ** 2 + X.imag.astype(np.float64) ** 2)
                pwr *= inv_s1_sq
                pwr_shifted = np.fft.fftshift(pwr, axes=1).astype(np.float32)

                # dBFS
                np.maximum(pwr_shifted, np.float32(1e-30), out=pwr_shifted)
                dbfs = (10.0 * np.log10(pwr_shifted, out=pwr_shifted)) + np.float32(cal_offset_db)

                # TODO: Emitir dbfs a la red / siguiente etapa. Por ahora calculamos max_hold global
                # como métrica para stdout
                max_dbfs = np.max(dbfs)
                frames_processed += b
                
                local_tail += 1
                tail.value = local_tail

                # Imprimir métricas de velocidad cada cierto tiempo
                if local_tail % 100 == 0:
                    elapsed = time.perf_counter() - t_start
                    fft_per_sec = frames_processed / elapsed
                    print(f"[Consumer] Procesados: {frames_processed} tramas | Vel: {fft_per_sec:.0f} FFT/s | Max Pico: {max_dbfs:.2f} dBFS")

            else:
                # Esperar datos (Backoff rápido)
                time.sleep(0.001)

        print(f"[Consumer] Terminado. Total tramas: {frames_processed}")

    finally:
        shm.close()

# --------------------------------------------------------------------------- #
# Productor (Replay)
# --------------------------------------------------------------------------- #
def producer_process(
    meta_path: Path,
    shm_name: str,
    shape: tuple[int, int],
    dtype: np.dtype,
    head: mp.Value,
    tail: mp.Value,
    stop_flag: mp.Value,
    replay_mode: str,
    chunk_samples: int
):
    shm = shared_memory.SharedMemory(name=shm_name)
    ring_buffer = np.ndarray(shape, dtype=dtype, buffer=shm.buf)
    capacity = shape[0]
    
    # Leer meta
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    fs = float(meta["global"].get("core:sample_rate", meta.get("captures", [{}])[0].get("core:sample_rate", 0)))
    datatype = meta["global"]["core:datatype"]
    base_dtype, _ = SIGMF_DTYPES[datatype]

    # Buscar archivo data
    stem = meta_path.name
    for suffix in (".sigmf-meta", ".meta", ".json"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    data_path = meta_path.with_name(f"{stem}.iq")
    if not data_path.exists():
        data_path = meta_path.with_name(f"{stem}.sigmf-data")

    # Memmap
    mm = np.memmap(data_path, dtype=base_dtype, mode="r")
    total_samples = mm.size // 2
    
    samples_per_chunk = chunk_samples
    num_chunks = total_samples // samples_per_chunk

    print(f"[Producer] Iniciando Replay ({replay_mode}). Archivo: {data_path.name} | Total chunks: {num_chunks}")

    overflow_drops = 0
    t_start = time.perf_counter()
    expected_time = 0.0

    local_head = 0

    try:
        for i in range(num_chunks):
            # Check overflow
            if local_head - tail.value >= capacity:
                overflow_drops += 1
                # Drop chunk y seguir adelante para no bloquear
                continue
            
            # Leer chunk
            start_idx = i * samples_per_chunk * 2
            end_idx = start_idx + samples_per_chunk * 2
            chunk_data = mm[start_idx:end_idx]

            # Escribir en ring buffer
            idx = local_head % capacity
            ring_buffer[idx] = chunk_data
            
            local_head += 1
            head.value = local_head

            if replay_mode == "realtime":
                expected_time += (samples_per_chunk / fs)
                elapsed = time.perf_counter() - t_start
                sleep_time = expected_time - elapsed
                if sleep_time > 0:
                    time.sleep(sleep_time)

        print(f"[Producer] EOF alcanzado. Overflows descartados: {overflow_drops}")
        stop_flag.value = 1

    finally:
        shm.close()

# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("meta", type=Path, help="Ruta al .sigmf-meta")
    ap.add_argument("-c", "--config", type=Path, default=Path("config/spectrogram_config.json"))
    ap.add_argument("--replay", choices=["fast", "realtime"], default="realtime", help="Modo de reproducción")
    args = ap.parse_args(argv)

    cfg = json.loads(args.config.read_bytes())
    fft_cfg = cfg["fft"]
    stream_cfg = cfg.get("streaming", {})

    nfft = int(fft_cfg["nfft"])
    overlap = float(fft_cfg["overlap"])
    hop = int(round(nfft * (1.0 - overlap)))
    
    batch_frames = int(stream_cfg.get("batch_frames", 256))
    capacity = int(stream_cfg.get("ring_capacity_batches", 128))

    # El productor entregará exactamente (batch_frames * hop) samples complejos por chunk.
    chunk_samples = batch_frames * hop

    meta = json.loads(args.meta.read_text(encoding="utf-8"))
    datatype = meta["global"]["core:datatype"]
    base_dtype, fullscale = SIGMF_DTYPES[datatype]

    # Shared Memory: Ring Buffer
    # Cada chunk es `chunk_samples * 2` elementos de `base_dtype` (I y Q interleavados)
    shape = (capacity, chunk_samples * 2)
    bytes_per_chunk = chunk_samples * 2 * base_dtype.itemsize
    total_bytes = capacity * bytes_per_chunk

    print(f"[*] Asignando Ring Buffer: {capacity} slots x {chunk_samples} samples. Total: {total_bytes / 1024 / 1024:.1f} MB")
    
    shm = shared_memory.SharedMemory(create=True, size=total_bytes)
    
    head = mp.Value('Q', 0)
    tail = mp.Value('Q', 0)
    stop_flag = mp.Value('i', 0)

    # Iniciar procesos
    p_producer = mp.Process(target=producer_process, args=(
        args.meta, shm.name, shape, base_dtype, head, tail, stop_flag, args.replay, chunk_samples
    ))
    
    p_consumer = mp.Process(target=consumer_process, args=(
        shm.name, shape, base_dtype, head, tail, stop_flag,
        nfft, hop, fft_cfg["window"], fft_cfg.get("window_arg"),
        fullscale, float(cfg.get("calibration", {}).get("cal_offset_db", 0.0)),
        bool(fft_cfg.get("remove_dc", False))
    ))

    p_consumer.start()
    p_producer.start()

    try:
        p_producer.join()
        p_consumer.join()
    except KeyboardInterrupt:
        print("\n[!] Interrumpido por el usuario.")
        stop_flag.value = 1
        p_producer.join()
        p_consumer.join()
    finally:
        shm.close()
        shm.unlink()
        print("[*] Memoria compartida liberada. Pipeline cerrado.")

    return 0

if __name__ == "__main__":
    raise SystemExit(main())
