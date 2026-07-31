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
import psutil
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
    last_chunk_size: mp.Value,
    nfft: int,
    hop: int,
    window_name: str,
    window_arg: float | None,
    fullscale: float,
    cal_offset_db: float,
    remove_dc: bool,
    fs: float,
    dump_npz: str | None
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
    history = None

    frames_processed = 0
    t_start = time.perf_counter()
    last_print_time = t_start
    last_frames_processed = 0
    
    required_ffts_per_sec = fs / hop

    local_tail = tail.value
    
    # Acumulador para --dump-npz
    dump_dbfs = [] if dump_npz else None

    try:
        while not stop_flag.value or local_tail < head.value:
            if local_tail < head.value:
                # Extraer chunk del ring buffer
                idx = local_tail % capacity
                raw = np.asarray(ring_buffer[idx], dtype=np.float32)
                z_chunk = raw.view(np.complex64) * scale

                # Truncate if it's the final partial chunk
                if stop_flag.value and local_tail == head.value - 1 and last_chunk_size.value > 0:
                    z_chunk = z_chunk[:last_chunk_size.value]

                # Cola de arrastre sin warm-up de ceros
                if history is None:
                    z = z_chunk
                else:
                    z = np.concatenate((history, z_chunk))
                    
                if len(z) < nfft:
                    history = z
                    local_tail += 1
                    tail.value = local_tail
                    continue

                history = z[-history_size:] # Guardar para el siguiente lote

                # Crear ventanas deslizantes (el cálculo automático ajusta b exacto)
                b = (len(z) - nfft) // hop + 1
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
                
                if dump_dbfs is not None:
                    dump_dbfs.append(dbfs)

                max_dbfs = np.max(dbfs)
                frames_processed += b
                
                local_tail += 1
                tail.value = local_tail

                # Imprimir métricas de velocidad cada 5.0 segundos
                current_time = time.perf_counter()
                if current_time - last_print_time >= 5.0:
                    elapsed = current_time - t_start
                    
                    # Ventana móvil para velocidad instantánea
                    delta_t = current_time - last_print_time
                    delta_frames = frames_processed - last_frames_processed
                    fft_per_sec = delta_frames / delta_t
                    
                    simulated_time = (frames_processed * hop) / fs
                    occupancy_pct = ((head.value - tail.value) / capacity) * 100.0
                    
                    process = psutil.Process()
                    rss_mb = process.memory_info().rss / 1024 / 1024
                    
                    print(f"[Consumer] "
                          f"Wall-clock: {elapsed:.1f}s | "
                          f"Señal procesada: {simulated_time:.1f}s | "
                          f"Ring: {occupancy_pct:.2f}% lleno | "
                          f"Vel Inst: {fft_per_sec:.0f} FFT/s (Req: {required_ffts_per_sec:.0f}) | "
                          f"RSS: {rss_mb:.1f} MB | "
                          f"Pico: {max_dbfs:.2f} dBFS", flush=True)
                    
                    last_print_time = current_time
                    last_frames_processed = frames_processed

            else:
                # Esperar datos (Backoff rápido)
                time.sleep(0.001)

        elapsed_total = time.perf_counter() - t_start
        print(f"[Consumer] Terminado. Total tramas: {frames_processed} en {elapsed_total:.2f}s")
        
        if dump_dbfs is not None and len(dump_dbfs) > 0:
            final_dbfs = np.concatenate(dump_dbfs, axis=0)
            times = (np.arange(frames_processed, dtype=np.float64) * hop + nfft / 2.0) / fs
            # Freqs requiere fc, pero podemos guardarlas como 0 si no lo tenemos a mano o no lo pasamos
            # Para facilitar, el test de equivalencia puede regenerar el vector de freqs.
            # Solo guardaremos dbfs y times_s
            np.savez(
                dump_npz,
                dbfs=final_dbfs,
                times_s=times
            )
            print(f"[Consumer] Matriz guardada en {dump_npz}")

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
    last_chunk_size: mp.Value,
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
    expected_dropped = total_samples - (num_chunks * samples_per_chunk)

    print(f"[Producer] Iniciando Replay ({replay_mode}). Archivo: {data_path.name} | Total chunks: {num_chunks} | Remanente EOF: {expected_dropped}")

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

        if expected_dropped > 0:
            print(f"[Producer] Flushing remanente de EOF sin padding: {expected_dropped} muestras.")
            
            # Check overflow for the final remainder
            while local_head - tail.value >= capacity:
                overflow_drops += 1
                time.sleep(0.001)

            start_idx = num_chunks * samples_per_chunk * 2
            end_idx = start_idx + expected_dropped * 2
            
            # We must assign to a pre-allocated chunk to maintain ring buffer slot size (shape matching),
            # but we won't process the zeros on the consumer side because we pass last_chunk_size
            chunk_data = np.empty(samples_per_chunk * 2, dtype=base_dtype)
            chunk_data[:expected_dropped * 2] = mm[start_idx:end_idx]
            
            idx = local_head % capacity
            ring_buffer[idx] = chunk_data
            
            local_head += 1
            head.value = local_head
            last_chunk_size.value = expected_dropped

        print(f"[Producer] EOF alcanzado. Overflows descartados: {overflow_drops}")
        stop_flag.value = 1

    finally:
        shm.close()

# --------------------------------------------------------------------------- #
# Productor (Live SDR)
# --------------------------------------------------------------------------- #
def producer_live_process(
    shm_name: str,
    shape: tuple[int, int],
    dtype: np.dtype,
    head: mp.Value,
    tail: mp.Value,
    stop_flag: mp.Value,
    last_chunk_size: mp.Value,
    freq: float,
    rate: float,
    gain: float,
    chunk_samples: int
):
    import SoapySDR
    shm = shared_memory.SharedMemory(name=shm_name)
    ring_buffer = np.ndarray(shape, dtype=dtype, buffer=shm.buf)
    capacity = shape[0]

    print(f"[Producer LIVE] Conectando a Harogic SDR. Freq: {freq/1e6:.1f} MHz, Rate: {rate/1e6:.2f} MSps", flush=True)

    sdr = SoapySDR.Device({"driver": "harogic"})
    direction = SoapySDR.SOAPY_SDR_RX
    canal = 0
    
    sdr.setSampleRate(direction, canal, rate)
    actual_rate = sdr.getSampleRate(direction, canal)
    print(f"[Producer LIVE] Rate pedido: {rate/1e6:.4f} MSps | Rate real: {actual_rate/1e6:.4f} MSps", flush=True)
    
    sdr.setFrequency(direction, canal, freq)
    sdr.setGain(direction, canal, gain)
    
    # IMPORTANTE: Pedimos SoapySDR_CS16 (int16 nativo del SDR)
    soapy_format = SoapySDR.SOAPY_SDR_CS16 if dtype == np.dtype("<i2") else SoapySDR.SOAPY_SDR_CF32
    
    rxStream = sdr.setupStream(direction, soapy_format)
    sdr.activateStream(rxStream)
    
    # Buffer temporal para SoapySDR
    buff = np.zeros(chunk_samples, np.complex64)
    if soapy_format == SoapySDR.SOAPY_SDR_CS16:
        buff_view = buff.view(np.int16)
    else:
        buff_view = buff

    overflow_drops = 0
    local_head = 0

    print("[Producer LIVE] 📡 Streaming INICIADO.", flush=True)

    try:
        while not stop_flag.value:
            if local_head - tail.value >= capacity:
                overflow_drops += 1
                time.sleep(0.001)
                continue

            # Leer del hardware
            sr = sdr.readStream(rxStream, [buff], chunk_samples, timeoutUs=1000000)
            
            if sr.ret > 0:
                # Escribir en ring buffer
                idx = local_head % capacity
                ring_buffer[idx][:sr.ret * 2] = buff_view[:sr.ret * 2]
                
                local_head += 1
                head.value = local_head
            elif sr.ret == SoapySDR.SOAPY_SDR_TIMEOUT:
                print("[Producer LIVE] ⚠️ TIMEOUT: No se recibieron datos del SDR en el último segundo.", flush=True)
            elif sr.ret == SoapySDR.SOAPY_SDR_OVERFLOW:
                overflow_drops += 1
                print("[Producer LIVE] ⚠️ OVERFLOW: El SDR perdió tramas.", flush=True)

    except KeyboardInterrupt:
        pass
    finally:
        print(f"[Producer LIVE] Apagando sensor. Overflows descartados: {overflow_drops}")
        sdr.deactivateStream(rxStream)
        sdr.closeStream(rxStream)
        shm.close()

# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    ap.add_argument("--meta", type=Path, help="Ruta al .sigmf-meta para Replay (Requerido si no usas --live)")
    ap.add_argument("--live", action="store_true", help="Activar modo en vivo (Hardware Harogic SDR)")
    ap.add_argument("--freq", type=float, default=2400e6, help="Frecuencia central en Hz (Solo para --live)")
    ap.add_argument("--rate", type=float, default=1.95e6, help="Tasa de muestreo en Hz (Solo para --live)")
    ap.add_argument("--gain", type=float, default=40.0, help="Ganancia SDR (Solo para --live)")
    ap.add_argument("-c", "--config", type=Path, default=Path("config/spectrogram_config.json"))
    ap.add_argument("--replay", choices=["fast", "realtime"], default="realtime", help="Modo de reproducción")
    ap.add_argument("--dump-npz", type=str, default=None, help="Exportar matriz a un archivo .npz")
    args = ap.parse_args(argv)

    if not args.live and not args.meta:
        ap.error("Debes especificar --meta para modo Replay o usar --live para Hardware SDR.")

    cfg = json.loads(args.config.read_bytes())
    fft_cfg = cfg["fft"]
    stream_cfg = cfg.get("streaming", {})

    nfft = int(fft_cfg["nfft"])
    overlap = float(fft_cfg["overlap"])
    hop = int(round(nfft * (1.0 - overlap)))
    
    batch_frames = int(stream_cfg.get("batch_frames", 256))
    capacity = int(stream_cfg.get("ring_capacity_batches", 128))

    chunk_samples = batch_frames * hop

    if args.live:
        # En vivo ahora asume CS16 (int16 nativo) para evitar float casting en el SDR
        base_dtype = np.dtype("<i2")
        fullscale = 32768.0
        fs = args.rate
    else:
        meta = json.loads(args.meta.read_text(encoding="utf-8"))
        datatype = meta["global"]["core:datatype"]
        base_dtype, fullscale = SIGMF_DTYPES[datatype]
        fs = float(meta["global"].get("core:sample_rate", meta.get("captures", [{}])[0].get("core:sample_rate", 0)))

    shape = (capacity, chunk_samples * 2)
    bytes_per_chunk = chunk_samples * 2 * base_dtype.itemsize
    total_bytes = capacity * bytes_per_chunk

    print(f"[*] Asignando Ring Buffer: {capacity} slots x {chunk_samples} samples. Total: {total_bytes / 1024 / 1024:.1f} MB", flush=True)
    
    shm = shared_memory.SharedMemory(create=True, size=total_bytes)
    
    head = mp.Value('Q', 0, lock=False)
    tail = mp.Value('Q', 0, lock=False)
    stop_flag = mp.Value('i', 0, lock=False)
    last_chunk_size = mp.Value('i', 0, lock=False)

    if args.live:
        p_producer = mp.Process(target=producer_live_process, args=(
            shm.name, shape, base_dtype, head, tail, stop_flag, last_chunk_size, args.freq, args.rate, args.gain, chunk_samples
        ))
    else:
        p_producer = mp.Process(target=producer_process, args=(
            args.meta, shm.name, shape, base_dtype, head, tail, stop_flag, last_chunk_size, args.replay, chunk_samples
        ))
    
    p_consumer = mp.Process(target=consumer_process, args=(
        shm.name, shape, base_dtype, head, tail, stop_flag, last_chunk_size,
        nfft, hop, fft_cfg["window"], fft_cfg.get("window_arg"),
        fullscale, float(cfg.get("calibration", {}).get("cal_offset_db", 0.0)),
        bool(fft_cfg.get("remove_dc", False)), fs, args.dump_npz
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
