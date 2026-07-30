import numpy as np

def peak_marker(dbfs_band: np.ndarray, freqs_band: np.ndarray) -> tuple[float, float]:
    """
    1.1 Pico / frecuencia central
    Retorna (pico_dbfs, freq_pico_hz).
    """
    idx = np.argmax(dbfs_band)
    return float(dbfs_band[idx]), float(freqs_band[idx])

def band_power_db(dbfs_band: np.ndarray, enbw_bins: float) -> float:
    """
    1.2 Potencia de banda (Channel Power)
    Suma linealmente los bins de dBFS en la banda y compensa la ganancia del ENBW.
    """
    # Convertir dBFS a lineal
    lineal = 10.0 ** (dbfs_band / 10.0)
    suma_lineal = np.sum(lineal)
    
    # Prevenir log de cero en caso extremo
    if suma_lineal <= 0:
        return -300.0
        
    # Corregir por ENBW y volver a dBFS
    return float(10.0 * np.log10(suma_lineal / enbw_bins))

def occupied_bandwidth(dbfs_band: np.ndarray, freqs_band: np.ndarray, threshold_db: float = -3.0) -> float:
    """
    1.3 Ancho de banda ocupado.
    Método: peak-based (busca pico, expande hasta -3 dB del pico).
    Esto es robusto para tonos puros; más preciso que cumsum% en presencia de lóbulos laterales.
    """
    if len(dbfs_band) == 0:
        return 0.0

    idx_peak = np.argmax(dbfs_band)
    peak_db = dbfs_band[idx_peak]

    # Umbral en dB respecto al pico
    threshold = peak_db + threshold_db

    # Buscar bordes donde cae por debajo del threshold
    idx_low = idx_peak
    while idx_low > 0 and dbfs_band[idx_low - 1] > threshold:
        idx_low -= 1

    idx_high = idx_peak
    while idx_high < len(dbfs_band) - 1 and dbfs_band[idx_high + 1] > threshold:
        idx_high += 1

    return float(freqs_band[idx_high] - freqs_band[idx_low])

def noise_floor_spectral(dbfs_frame: np.ndarray, band_idx_start: int, band_idx_end: int, guard_bins: int = 5, measure_bins: int = 20) -> float:
    """
    1.4a Estimador de piso Espectral (para señales continuas).
    Toma la mediana de potencia en bins adyacentes a la banda en el MISMO frame.
    """
    n_bins = len(dbfs_frame)
    
    left_start = max(0, band_idx_start - guard_bins - measure_bins)
    left_end = max(0, band_idx_start - guard_bins)
    
    right_start = min(n_bins, band_idx_end + guard_bins)
    right_end = min(n_bins, right_start + measure_bins)
    
    left_samples = dbfs_frame[left_start:left_end]
    right_samples = dbfs_frame[right_start:right_end]
    
    combined = np.concatenate([left_samples, right_samples])
    if len(combined) == 0:
        return -300.0
        
    return float(np.median(combined))

def noise_floor_temporal(dbfs_band_history: np.ndarray) -> float:
    """
    1.4b Estimador de piso Temporal (para burst/intermitentes).
    Toma la mediana de potencia de la banda en tramas marcadas como "silencio" (ventana de referencia).
    Para el análisis batch off-line, pasamos un array histórico de bins de silencio.
    """
    if len(dbfs_band_history) == 0:
        return -300.0
    return float(np.median(dbfs_band_history))

class PresenceDetector:
    """
    1.5 Lógica de Presencia (con histéresis).
    Mantiene estado a lo largo del tiempo trama a trama.
    """
    def __init__(self, margin_on_db: float, margin_off_db: float, required_consecutive: int = 3):
        self.margin_on = margin_on_db
        self.margin_off = margin_off_db
        self.required_consecutive = required_consecutive
        
        self.is_present = False
        self.consecutive_high = 0
        self.consecutive_low = 0
        
    def update(self, snr_db: float) -> bool:
        """
        Retorna True si la señal se considera presente en el frame actual.
        El SNR ya es snr = potencia_banda - piso_ruido.
        Por ende, comparamos el SNR directamente contra los márgenes.
        """
        if self.is_present:
            # Buscamos condiciones de apagado
            if snr_db < self.margin_off:
                self.consecutive_low += 1
                if self.consecutive_low >= self.required_consecutive:
                    self.is_present = False
                    self.consecutive_low = 0
            else:
                self.consecutive_low = 0
        else:
            # Buscamos condiciones de encendido
            if snr_db >= self.margin_on:
                self.consecutive_high += 1
                if self.consecutive_high >= self.required_consecutive:
                    self.is_present = True
                    self.consecutive_high = 0
            else:
                self.consecutive_high = 0
                
        return self.is_present
