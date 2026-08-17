import json, shutil, os
from pathlib import Path

src = Path("rf-spectrum/data/samples/session_20260814_103140_106.5MHz")
dst = Path("rf-spectrum/data/samples/session_replay_106.5MHz")

if dst.exists():
    shutil.rmtree(dst)
dst.mkdir(parents=True)

shutil.copy(src / "captura_106.5MHz_part001.iq", dst / "captura_106.5MHz_part001.iq")
with open(src / "captura_106.5MHz_part001.sigmf-meta", "r") as f:
    meta = json.load(f)
meta["global"]["core:session_id"] = "session_replay_106.5MHz"
with open(dst / "captura_106.5MHz_part001.sigmf-meta", "w") as f:
    json.dump(meta, f)
