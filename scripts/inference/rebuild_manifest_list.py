#!/usr/bin/env python3
import hashlib
import json


def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


entries = [
    {
        "name": "perception.depth",
        "path": "artifacts/onnx/depth_e24.onnx",
        "sha256": sha("artifacts/onnx/depth_e24.onnx"),
    },
    {
        "name": "control.policy",
        "path": "artifacts/onnx/policy_dummy.onnx",
        "sha256": sha("artifacts/onnx/policy_dummy.onnx"),
    },
]

with open("deploy/models/manifest.json", "w") as f:
    json.dump(entries, f, indent=2, sort_keys=True)
print("[OK] wrote list-style manifest with", len(entries), "entries")
