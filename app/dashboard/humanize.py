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
    margen_db = evento.get("pico_dbfs", 0) - (-40)  # Asume piso ~-40 dBFS
    severidad = evento.get("severidad", "low")
    duracion = evento.get("duration_s", 0)

    sev_label = get_severidad(severidad)

    return (
        f"La potencia detectada en la banda {evento.get('band_name', '?')} "
        f"superó el nivel de ruido esperado por aproximadamente {margen_db:.0f} dB "
        f"durante {duracion:.2f} segundos seguidos. "
        f"Esto se clasifica como {sev_label['descripcion'].lower()}."
    )
