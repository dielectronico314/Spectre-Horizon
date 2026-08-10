import sqlite3
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Ubicación por defecto de la base de datos
# Desarrollo: ./data/index.sqlite
# Producción: override con variable de entorno DB_PATH
DATA_ROOT = Path(__file__).parent.parent.parent / "data"
DB_PATH = DATA_ROOT / "index.sqlite"

SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    session_id            TEXT PRIMARY KEY,
    capture_sha256        TEXT NOT NULL,
    fc_hz                 REAL,
    fs_hz                 REAL,
    start_datetime        TEXT,
    duration_s            REAL,
    n_events              INTEGER,
    ruta_meta             TEXT,
    tuvo_interrupciones   BOOLEAN DEFAULT 0
);

CREATE TABLE IF NOT EXISTS events (
    event_id                    TEXT PRIMARY KEY,
    session_id                  TEXT REFERENCES sessions(session_id),
    band_name                   TEXT,
    rule_name                   TEXT,
    start_t_s                   REAL,
    end_t_s                     REAL,
    duration_s                  REAL,
    pico_dbfs                   REAL,
    potencia_media_activa_dbfs  REAL,
    piso_ruido_dbfs             REAL,
    severidad                   TEXT,
    confianza                   REAL,
    closed_reason               TEXT,
    ruta_evidencia              TEXT
);

CREATE INDEX IF NOT EXISTS idx_events_session   ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_severidad ON events(severidad);
CREATE INDEX IF NOT EXISTS idx_events_start     ON events(start_t_s);
CREATE INDEX IF NOT EXISTS idx_sessions_fecha   ON sessions(start_datetime);
"""

def get_db_connection() -> sqlite3.Connection:
    """
    Retorna una conexión a SQLite configurada con row_factory para diccionarios.
    Asegura que el directorio exista.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Inicializa el esquema de la base de datos si no existe.
    """
    conn = get_db_connection()
    try:
        conn.executescript(SCHEMA)
        conn.commit()
        logger.info(f"Base de datos inicializada en {DB_PATH}")
    finally:
        conn.close()

if __name__ == "__main__":
    init_db()
