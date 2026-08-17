import json
from pathlib import Path
import shutil

evidence_dir = Path("data/evidence")
for d in evidence_dir.iterdir():
    if d.is_dir() and "_" in d.name:
        manifest = d / "manifest.json"
        if manifest.exists():
            with open(manifest, 'r') as f:
                data = json.load(f)
            session_id = data["event_metadata"]["session_id"]
            event_id = data["event_metadata"]["event_id"]
            expected_name = f"{session_id}_{event_id}"
            
            if d.name == event_id:
                new_path = evidence_dir / expected_name
                print(f"Renombrando {d.name} -> {expected_name}")
                d.rename(new_path)
