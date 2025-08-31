#!/usr/bin/env python3
import json, hashlib
def sha(p): 
    with open(p,"rb") as f: return hashlib.sha256(f.read()).hexdigest()
d={
  "perception.depth": {
    "path":"artifacts/onnx/depth_e24.onnx",
    "sha256":sha("artifacts/onnx/depth_e24.onnx")
  },
  "control.policy": {
    "path":"artifacts/onnx/policy_dummy.onnx",
    "sha256":sha("artifacts/onnx/policy_dummy.onnx")
  }
}
with open("deploy/models/manifest.json","w") as f:
    json.dump(d,f,indent=2,sort_keys=True)
print("[OK] wrote deploy/models/manifest.json (dotted-keys dict)")
