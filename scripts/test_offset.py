import numpy as np
oracle = np.load('/workspace/tests/day12_validation/captura_106.5MHz_part001_espectrograma.npz')["dbfs"]
stream = np.load('/workspace/tests/day12_validation/stream_dump.npz')["dbfs"]

print("Oracle 0:", oracle[0, :5])
print("Stream 0:", stream[0, :5])
print("Stream 1:", stream[1, :5])
print("Stream 2:", stream[2, :5])

diff1 = np.abs(oracle[0] - stream[1])
print("Max diff at offset 1:", np.max(diff1))
