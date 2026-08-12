import json
import sqlite3
from pathlib import Path

db = sqlite3.connect("data/index.sqlite")
cursor = db.cursor()

for f in Path("data/evidence").glob("*/manifest.json"):
    try:
        data = json.loads(f.read_text())
        sid = data.get("event_metadata", {}).get("session_id")
        if not sid:
            print(f"HUÉRFANO (sin session_id): {f}")
            continue
        cursor.execute("SELECT 1 FROM sessions WHERE session_id=?", (sid,))
        if not cursor.fetchone():
            print(f"HUÉRFANO (no en db): {f} -> {sid}")
    except Exception as e:
        print(f"Error parseando {f}: {e}")
