#!/usr/bin/env python3
import argparse
import hashlib
import json

p = argparse.ArgumentParser()
p.add_argument("--manifest", required=True)
p.add_argument("--model-key", required=True)  # e.g. perception.depth
p.add_argument("--file", required=True)
a = p.parse_args()
sha = hashlib.sha256(open(a.file, "rb").read()).hexdigest()
m = json.load(open(a.manifest))
dot_sha = f"{a.model_key}.sha256"
dot_path = f"{a.model_key}.path"
if dot_sha in m or dot_path in m:
    m[dot_sha] = sha
    m[dot_path] = a.file
else:
    d = m
    for k in a.model_key.split("."):
        d = d.setdefault(k, {})
    d["sha256"] = sha
    d["path"] = a.file
json.dump(m, open(a.manifest, "w"), indent=2, sort_keys=True)
print(f"updated {a.manifest}: {a.model_key}.sha256={sha}")
