import json
from pathlib import Path
import onnxruntime as ort

m = json.load(open("deploy/models/manifest.json"))
if isinstance(m, dict):
    items = [{"name": k, **v} for k, v in m.items()]
elif isinstance(m, list):
    items = m
else:
    raise AssertionError("manifest must be dict or list")

assert items, "manifest is empty"
for e in items:
    p = Path(e.get("dst") or e.get("path"))
    assert p.is_file(), f"missing file: {p}"
    ort.InferenceSession(p.as_posix(), providers=["CPUExecutionProvider"])
