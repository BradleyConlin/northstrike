#!/usr/bin/env python3
import json, hashlib

def sha(p):
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()

depth = "artifacts/onnx/depth_e24.onnx"
policy = "artifacts/onnx/policy_dummy.onnx"

out = {
  "perception": {"depth": {"path": depth, "sha256": sha(depth)}},
  "control": {"policy": {"path": policy, "sha256": sha(policy)}},
}

with open("deploy/models/manifest.json", "w") as f:
    json.dump(out, f, indent=2, sort_keys=True)
print("[OK] wrote deploy/models/manifest.json with 2 models")
