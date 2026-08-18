"""
humanize.py — Traducción de jerga técnica a lenguaje para no técnicos.
Tabla centralizada de mapeos: dato técnico → descripción comprensible.
"""

SEVERIDAD_LABELS = {
    "low": {"icon": "🟡", "texto": "Baja", "descripcion": "Señal débil, apenas por encima del ruido"},
    "medium": {"icon": "🟠", "texto": "Media", "descripcion": "Señal clara, moderadamente por encima del ruido"},
    "high": {"icon": "🔴", "texto": "Alta", "descripcion": "Señal muy fuerte, muy por encima del ruido"},
}

CLOSED_REASON_LABELS = {
    "threshold_off": "Señal terminó de forma natural",
    "end_of_capture": "La grabación terminó mientras la señal seguía activa",
}

CONFIANZA_LABELS = {
    0.0: "Muy baja",
    0.25: "Baja",
    0.5: "Media",
    0.75: "Alta",
    1.0: "Muy alta",
}

def get_severidad(severidad_key: str) -> dict:
    """Retorna icon, texto, descripcion para una severidad."""
    return SEVERIDAD_LABELS.get(severidad_key, {"icon": "?", "texto": "Desconocida", "descripcion": ""})

def get_confianza_label(confianza: float) -> str:
    """Clasifica confianza numérica en tramos."""
    if confianza >= 0.9:
        return CONFIANZA_LABELS[1.0]
    elif confianza >= 0.75:
        return CONFIANZA_LABELS[0.75]
    elif confianza >= 0.5:
        return CONFIANZA_LABELS[0.5]
    elif confianza >= 0.25:
        return CONFIANZA_LABELS[0.25]
    else:
        return CONFIANZA_LABELS[0.0]

def get_closed_reason(reason: str) -> str:
    """Traduce closed_reason a lenguaje humano."""
    return CLOSED_REASON_LABELS.get(reason, f"Cierre por: {reason}")

def explain_evento(evento: dict) -> str:
    """
    Genera explicación humana de por qué se generó un evento.
    Usa snr_margin_db inferido de pico_dbfs y potencia_media_activa_dbfs.
    """
    piso_ruido_dbfs = evento.get("piso_ruido_dbfs")
    severidad = evento.get("severidad", "low")
    duracion = evento.get("duration_s", 0)
    sev_label = get_severidad(severidad)

    if piso_ruido_dbfs is None:
        return (
            f"La potencia detectada en la banda {evento.get('band_name', '?')} "
            f"superó el umbral durante {duracion:.2f} segundos seguidos, "
            f"pero el margen de ruido exacto no está disponible para este evento antiguo. "
            f"Esto se considera como {sev_label['descripcion'].lower()}."
        )

    margen_db = evento.get("pico_dbfs", 0) - piso_ruido_dbfs
    explicacion = (
        f"La potencia detectada en la banda {evento.get('band_name', '?')} "
        f"superó el nivel de ruido esperado por aproximadamente {margen_db:.0f} dB "
        f"durante {duracion:.2f} segundos seguidos. "
        f"Esto se considera como {sev_label['descripcion'].lower()}."
    )
    
    # Documentar explícitamente el tono continuo sintético del Golden Dataset
    if evento.get("session_id") == "session_golden_demo_v1" and evento.get("band_name") == "CW_Tone":
        explicacion += " (Nota: Este tono es sintético y deliberadamente continuo para fines de validación, no es un artefacto de fuga del oscilador local)."
        
    return explicacion

def get_spectrum_category(fc_hz: float) -> str:
    """Clasifica una frecuencia central en su banda de espectro oficial."""
    if not fc_hz:
        return "Desconocido"
    
    mhz = fc_hz / 1e6
    if mhz < 0.03:
        return "VLF"
    elif 0.03 <= mhz < 0.3:
        return "LF"
    elif 0.3 <= mhz < 3:
        return "MF"
    elif 3 <= mhz < 30:
        return "HF"
    elif 30 <= mhz < 300:
        return "VHF"
    elif 300 <= mhz < 3000:
        return "UHF"
    elif 3000 <= mhz < 30000:
        return "SHF"
    elif 30000 <= mhz <= 40000:
        return "EHF"
    return "Fuera de Rango"

def format_freq_mhz(fc_hz: float) -> str:
    """Convierte Hz a MHz humanizados con 1 o 2 decimales."""
    if not fc_hz:
        return "N/A"
    mhz = fc_hz / 1e6
    if mhz.is_integer() or round(mhz, 1) == mhz:
        return f"{mhz:.1f} MHz"
    return f"{mhz:.2f} MHz"
