import json
from pathlib import Path

events = []
for p in Path(".").glob("eventos_*.json"):
    events.extend(json.loads(p.read_text()))

piso_map = {e["event_id"]: e["piso_ruido_dbfs"] for e in events if "piso_ruido_dbfs" in e}

for f in Path("data/evidence").glob("*/manifest.json"):
    data = json.loads(f.read_text())
    ev_id = data.get("event_metadata", {}).get("event_id")
    if ev_id in piso_map:
        data["event_metadata"]["piso_ruido_dbfs"] = piso_map[ev_id]
        f.write_text(json.dumps(data, indent=4))
        print(f"Patched {ev_id}")
    else:
        print(f"Warning: {ev_id} not found in regenerations")
