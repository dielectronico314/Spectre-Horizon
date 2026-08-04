"""
EventEngine — máquina de estados pura para detección de eventos por regla de umbral.

Sin I/O: no lee CSV ni JSON. Recibe métricas ya calculadas por trama (Día 13:
app/processing/features.py) y decide inicio/actualización/cierre de eventos.

Decisión de diseño (ver docs/EVENTS_REF.md sección "Espacio de decisión: SNR
en vez de dBFS absoluto"): la regla y la severidad operan sobre `snr_db`
(potencia_banda - piso_ruido, ya calculado en Día 13) en vez de recomputar
`umbral_on_dB = piso_ruido_dB + margen_dB` en dBFS absoluto. Es matemáticamente
equivalente para la decisión on/off (potencia >= piso + margen  <=>  snr >= margen)
y evita reimplementar el estimador de piso (spectral | temporal) dentro del
motor de eventos — se reutiliza el que ya se eligió por banda en Día 13.
"""

from enum import Enum


class EventState(Enum):
    IDLE = "IDLE"
    ACTIVO = "ACTIVO"
    COOLDOWN = "COOLDOWN"


class EventEngine:
    """
    Motor de eventos para UNA banda. Se alimenta trama a trama, en orden
    temporal, vía process_frame(). Al terminar la sesión hay que llamar
    flush() una vez para cerrar cualquier evento que quede en curso.
    """

    def __init__(
        self,
        band_name: str,
        margen_umbral_db: float,
        min_on_frames: int = 3,
        min_off_frames: int = 3,
        merge_gap_s: float = 0.5,
        margen_severidad_medium_db: float = 6.0,
        margen_severidad_high_db: float = 12.0,
        confianza_escala_db: float = 10.0,
        session_id: str = "",
        capture_sha256: str = "",
    ):
        self.band_name = band_name
        self.margen_umbral_db = margen_umbral_db
        self.min_on_frames = min_on_frames
        self.min_off_frames = min_off_frames
        self.merge_gap_s = merge_gap_s
        self.margen_severidad_medium_db = margen_severidad_medium_db
        self.margen_severidad_high_db = margen_severidad_high_db
        self.confianza_escala_db = confianza_escala_db
        self.session_id = session_id
        self.capture_sha256 = capture_sha256

        self.state = EventState.IDLE
        self._pending_on = []  # [(t_s, snr_db, pico_dbfs, potencia_dbfs)] mientras se confirma el inicio
        self._consecutive_low = 0
        self._cooldown_since_t = None
        self._event_counter = 0
        self._event = None  # evento en curso (dict acumulador con claves privadas _*)

    # ------------------------------------------------------------------ #
    # Internos
    # ------------------------------------------------------------------ #
    def _next_event_id(self) -> str:
        # Usa los primeros 12 caracteres del SHA256 de la captura cruda
        # para garantizar unicidad global sin depender del nombre de sesión.
        self._event_counter += 1
        hash_prefix = self.capture_sha256[:12] if self.capture_sha256 else "unknown"
        return f"{hash_prefix}_{self.band_name}_{self._event_counter:04d}"

    def _new_event(self) -> dict:
        return {
            "event_id": self._next_event_id(),
            "session_id": self.session_id,
            "band_name": self.band_name,
            "rule_name": "power_threshold",
            "capture_sha256": self.capture_sha256,
            "start_t_s": None,
            "_last_active_t_s": None,
            "_pico_dbfs": float("-inf"),
            "_pico_snr_db": float("-inf"),
            "_sum_potencia_dbfs": 0.0,
            "_sum_snr_db": 0.0,
            "_n_active_frames": 0,
            "n_fusiones": 0,
        }

    def _accumulate(self, event: dict, t_s: float, snr_db: float, pico_dbfs: float, potencia_dbfs: float) -> None:
        if event["start_t_s"] is None:
            event["start_t_s"] = t_s
        event["_last_active_t_s"] = t_s
        event["_pico_dbfs"] = max(event["_pico_dbfs"], pico_dbfs)
        event["_pico_snr_db"] = max(event["_pico_snr_db"], snr_db)
        event["_sum_potencia_dbfs"] += potencia_dbfs
        event["_sum_snr_db"] += snr_db
        event["_n_active_frames"] += 1

    def _finalize(self, event: dict, closed_reason: str) -> dict:
        n = event["_n_active_frames"]
        potencia_media_activa_dbfs = event["_sum_potencia_dbfs"] / n
        margen_medio_snr_db = (event["_sum_snr_db"] / n) - self.margen_umbral_db
        margen_pico_snr_db = event["_pico_snr_db"] - self.margen_umbral_db

        if margen_pico_snr_db >= self.margen_severidad_high_db:
            severidad = "high"
        elif margen_pico_snr_db >= self.margen_severidad_medium_db:
            severidad = "medium"
        else:
            severidad = "low"

        confianza = max(0.0, min(1.0, margen_medio_snr_db / self.confianza_escala_db))

        return {
            "event_id": event["event_id"],
            "session_id": event["session_id"],
            "band_name": event["band_name"],
            "rule_name": event["rule_name"],
            "capture_sha256": event["capture_sha256"],
            "start_t_s": event["start_t_s"],
            "end_t_s": event["_last_active_t_s"],
            "duration_s": event["_last_active_t_s"] - event["start_t_s"],
            "pico_dbfs": event["_pico_dbfs"],
            "potencia_media_activa_dbfs": potencia_media_activa_dbfs,
            "severidad": severidad,
            "confianza": confianza,
            "n_fusiones": event["n_fusiones"],
            "closed_reason": closed_reason,
        }

    def _reset_after_close(self) -> None:
        self._event = None
        self.state = EventState.IDLE
        self._cooldown_since_t = None
        self._consecutive_low = 0
        self._pending_on = []

    # ------------------------------------------------------------------ #
    # API pública
    # ------------------------------------------------------------------ #
    def process_frame(self, t_s: float, snr_db: float, pico_dbfs: float, potencia_dbfs: float):
        """
        Procesa una trama de esta banda. Retorna un dict de evento cerrado
        si en esta trama se confirma el cierre definitivo; si no, None.
        """
        if self.state == EventState.IDLE:
            if snr_db >= self.margen_umbral_db:
                self._pending_on.append((t_s, snr_db, pico_dbfs, potencia_dbfs))
                if len(self._pending_on) >= self.min_on_frames:
                    self._event = self._new_event()
                    for pt, psnr, ppk, ppw in self._pending_on:
                        self._accumulate(self._event, pt, psnr, ppk, ppw)
                    self._pending_on = []
                    self.state = EventState.ACTIVO
            else:
                self._pending_on = []
            return None

        if self.state == EventState.ACTIVO:
            if snr_db >= self.margen_umbral_db:
                self._accumulate(self._event, t_s, snr_db, pico_dbfs, potencia_dbfs)
                self._consecutive_low = 0
            else:
                # Tramas por debajo del umbral durante el conteo hacia OFF no
                # se acumulan: last_active_t_s/pico/potencia solo reflejan la
                # ventana genuinamente activa (evita inflar duracion_s con el
                # dwell de apagado). El estado sigue en ACTIVO hasta confirmar.
                self._consecutive_low += 1
                if self._consecutive_low >= self.min_off_frames:
                    self.state = EventState.COOLDOWN
                    self._cooldown_since_t = t_s
                    self._consecutive_low = 0
            return None

        # COOLDOWN
        if snr_db >= self.margen_umbral_db:
            self._event["n_fusiones"] += 1
            self._accumulate(self._event, t_s, snr_db, pico_dbfs, potencia_dbfs)
            self.state = EventState.ACTIVO
            self._consecutive_low = 0
            self._cooldown_since_t = None
            return None

        if t_s - self._cooldown_since_t >= self.merge_gap_s:
            closed = self._finalize(self._event, "threshold_off")
            self._reset_after_close()
            return closed

        return None

    def flush(self):
        """
        Fuerza el cierre de un evento en curso al terminar la captura
        (estado ACTIVO o COOLDOWN). Debe llamarse exactamente una vez,
        después de procesar la última trama de la sesión.
        """
        if self.state in (EventState.ACTIVO, EventState.COOLDOWN) and self._event is not None:
            closed = self._finalize(self._event, "end_of_capture")
            self._reset_after_close()
            return closed
        return None
