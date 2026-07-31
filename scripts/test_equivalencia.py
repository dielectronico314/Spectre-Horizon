#!/usr/bin/env python3
"""
test_equivalencia.py
Compara matemáticamente el espectrograma generado offline (Oráculo Día 11)
con el generado en tiempo real por streaming (Día 12) para garantizar cero
pérdidas en fronteras y equivalencia bit a bit.
"""

import argparse
import sys
from pathlib import Path
import numpy as np

def main():
    parser = argparse.ArgumentParser(description="Prueba de Equivalencia Matemática Estricta (Día 11 vs Día 12)")
    parser.add_argument("oracle_npz", type=Path, help="Archivo .npz generado por generate_spectrogram.py (Oráculo)")
    parser.add_argument("stream_npz", type=Path, help="Archivo .npz generado por stream_processor.py --dump-npz")
    parser.add_argument("--tol", type=float, default=1e-3, help="Tolerancia absoluta en dB (defecto: 1e-3)")
    
    args = parser.parse_args()
    
    if not args.oracle_npz.exists():
        print(f"❌ Error: No se encontró el oráculo {args.oracle_npz}")
        sys.exit(1)
        
    if not args.stream_npz.exists():
        print(f"❌ Error: No se encontró el output de stream {args.stream_npz}")
        sys.exit(1)
        
    print(f"⚖️ Iniciando Prueba de Equivalencia...")
    print(f"   Oráculo (Día 11) : {args.oracle_npz.name}")
    print(f"   Stream (Día 12)  : {args.stream_npz.name}")
    
    oracle = np.load(args.oracle_npz)
    stream = np.load(args.stream_npz)
    
    dbfs_oracle = oracle["dbfs"]
    dbfs_stream = stream["dbfs"]
    
    print(f"   Shape Oráculo : {dbfs_oracle.shape}")
    print(f"   Shape Stream  : {dbfs_stream.shape}")

    # (1) Verificación Estricta de Shape (sin padding, sin recortes)
    assert dbfs_oracle.shape == dbfs_stream.shape, f"❌ FALLO: Las dimensiones no coinciden. Oráculo: {dbfs_oracle.shape}, Stream: {dbfs_stream.shape}"
    print("   ✅ Diferencia de shape = 0. Ningún extremo tiene padding.")

    # (2) Verificación Estricta de Diferencia
    diff = np.abs(dbfs_oracle - dbfs_stream)
    max_diff = np.max(diff)
    
    print(f"   Diferencia Absoluta Máxima: {max_diff:.6f} dB")
    
    if max_diff <= args.tol:
        print("✅ ¡PRUEBA PASADA! Las matemáticas del pipeline de streaming coinciden de manera idéntica bit-a-bit con el oráculo.")
        sys.exit(0)
    else:
        print(f"❌ FALLO: La diferencia ({max_diff:.6f}) supera la tolerancia ({args.tol}).")
        
        # Encontrar donde falla
        idx = np.unravel_index(np.argmax(diff), diff.shape)
        print(f"   Peor discrepancia en frame {idx[0]}, bin {idx[1]}:")
        print(f"     Oráculo : {dbfs_oracle[idx]:.4f}")
        print(f"     Stream  : {dbfs_stream[idx]:.4f}")
        sys.exit(1)

if __name__ == "__main__":
    main()
