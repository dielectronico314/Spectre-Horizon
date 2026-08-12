from pydantic import BaseModel, Field, HttpUrl
from typing import List, Optional, Literal
from datetime import date, datetime

class HealthResponse(BaseModel):
    status: str = Field(..., example="ok")
    version: str = Field(..., example="0.1.0")

class SensorStatusResponse(BaseModel):
    ultima_sesion: Optional[str] = Field(None, example="captura_106.5MHz_20260720_153534")
    ultima_captura_utc: Optional[str] = Field(None, example="2026-07-20T15:35:36.459378Z")
    en_vivo: bool = Field(False, description="Flag indicando si hay un proceso live escribiendo actualmente. Normalmente false en despliegue analitico.")
    eventos_totales: int = Field(0, example=143)
    sensor_conectado: bool = Field(False, description="Indica si el sensor físico fue detectado en el bus USB.")

class EvidenceLinks(BaseModel):
    event_id: str = Field(..., example="19c10fbb7b7e_FM_Sub1_0001")
    archivos: dict[str, str] = Field(
        ...,
        description="URLs relativas al servidor (no rutas de disco absoluto) para descargar los archivos que componen el paquete",
        example={
            "manifest": "/events/19c10fbb7b7e_FM_Sub1_0001/evidence/manifest.json",
            "resumen": "/events/19c10fbb7b7e_FM_Sub1_0001/evidence/resumen.md",
            "espectrograma": "/events/19c10fbb7b7e_FM_Sub1_0001/evidence/espectrograma_evento.png",
            "iq_selectivo": "/events/19c10fbb7b7e_FM_Sub1_0001/evidence/evento.sigmf-data",
            "features": "/events/19c10fbb7b7e_FM_Sub1_0001/evidence/features_evento.csv"
        }
    )

class EventoResponse(BaseModel):
    event_id: str = Field(..., example="19c10fbb7b7e_FM_Sub1_0001")
    session_id: str = Field(..., example="captura_106.5MHz_20260720_153534_espectrograma")
    band_name: str = Field(..., example="FM_Sub1")
    rule_name: str = Field(..., example="power_threshold")
    start_t_s: float = Field(..., example=0.000262)
    end_t_s: float = Field(..., example=2.029781)
    duration_s: float = Field(..., example=2.03)
    pico_dbfs: float = Field(..., example=-104.13)
    potencia_media_activa_dbfs: float = Field(..., example=-103.34)
    severidad: Literal["low", "medium", "high"] = Field(..., description="Basado en margen sobre el piso de ruido")
    confianza: float = Field(..., ge=0.0, le=1.0, description="Satura en 1.0 para margenes >= confianza_escala_db (default 10dB)")
    closed_reason: str = Field(..., example="end_of_capture")

class SessionResponse(BaseModel):
    session_id: str = Field(..., example="captura_106.5MHz_20260720_153534_espectrograma")
    capture_sha256: str = Field(..., example="19c10fbb7b7e9ce3c9c277b503a9908809cc078d64c09fea47371e0f2365c0d0")
    fc_hz: Optional[float] = Field(None, example=106500000.0)
    fs_hz: Optional[float] = Field(None, example=1953125.0)
    start_datetime: Optional[str] = Field(None, example="2026-07-20T15:35:36.459378Z")
    duration_s: Optional[float] = Field(None, example=5.0)
    n_events: int = Field(..., example=10)
    tuvo_interrupciones: bool = Field(default=False, example=False, description="Si detectó gaps temporales entre eventos indicando interrupciones de captura")

class SessionDetailResponse(SessionResponse):
    eventos: List[str] = Field(..., description="Lista de event_id asociados a esta sesion")
