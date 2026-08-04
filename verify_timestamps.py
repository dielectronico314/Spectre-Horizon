import numpy as np
import pandas as pd
import sys

npz_path = "/workspace/tests/day13_synthetic/test_burst_espectrograma.npz"
csv_path = "/workspace/tests/day13_synthetic/features_test_burst_espectrograma.csv"

print(f"Cargando {npz_path}...")
try:
    npz = np.load(npz_path)
    times_s = npz['times_s']
except Exception as e:
    print(f"Error cargando NPZ: {e}")
    sys.exit(1)

print(f"Cargando {csv_path}...")
df = pd.read_csv(csv_path)

print(f"Shape NPZ times_s: {times_s.shape}")
print(f"Shape CSV: {df.shape}")

# El CSV puede tener múltiples filas por frame si hay múltiples bandas, filtramos por la primera banda
band1 = df['band_name'].unique()[0]
df_band = df[df['band_name'] == band1].reset_index(drop=True)

print(f"Shape CSV (Banda {band1}): {df_band.shape}")

diffs = []
for k in [0, 10, 100, 1000, len(df_band)-1]:
    t_csv = df_band.loc[k, 't_s']
    t_npz = times_s[k]
    diff = abs(t_csv - t_npz)
    diffs.append(diff)
    print(f"Frame {k}: CSV t_s = {t_csv:.6f}, NPZ times_s = {t_npz:.6f}, Diff = {diff:.6f}")

print(f"Max Diff: {max(diffs):.6f}")
