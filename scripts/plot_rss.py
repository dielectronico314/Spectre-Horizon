import re
import matplotlib.pyplot as plt

log_file = "/workspace/soak_30min.log"
out_file = "/workspace/tests/day13_results/rss_plot.png"

times = []
rss_vals = []

with open(log_file, "r") as f:
    for line in f:
        # Buscamos lineas como: [Consumer] Wall-clock: 2048.4s | ... | RSS: 159.0 MB | ...
        m = re.search(r"Wall-clock:\s*([\d\.]+)s.*RSS:\s*([\d\.]+)\s*MB", line)
        if m:
            t = float(m.group(1)) / 60.0  # Convertir a minutos
            r = float(m.group(2))
            times.append(t)
            rss_vals.append(r)

if times:
    plt.figure(figsize=(10, 5))
    plt.plot(times, rss_vals, label="Memoria RSS (MB)", color="blue", linewidth=1.5)
    plt.title("Estabilidad de Memoria (RSS) durante Soak Test de 37 mins")
    plt.xlabel("Tiempo (Minutos)")
    plt.ylabel("Uso de RAM (MB)")
    plt.grid(True, linestyle="--", alpha=0.7)
    
    # Ajustar limites Y para que el grafico no exagere fluctuaciones minimas
    y_mean = sum(rss_vals)/len(rss_vals)
    plt.ylim(max(0, y_mean - 50), y_mean + 50)
    
    plt.legend()
    plt.tight_layout()
    plt.savefig(out_file)
    print(f"Plot guardado en {out_file}")
else:
    print("No se encontraron datos en el log.")
