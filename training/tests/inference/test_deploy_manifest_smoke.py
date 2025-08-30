import json
from pathlib import Path
import onnxruntime as ort

m = json.load(open("deploy/models/manifest.json"))
assert isinstance(m, list) and m, "manifest must be a non-empty list"

for e in m:
    p = Path(e["path"])
    assert p.is_file(), f"missing file: {p}"
    ort.InferenceSession(p.as_posix(), providers=["CPUExecutionProvider"])
