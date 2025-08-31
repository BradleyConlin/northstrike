#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import time


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def scan(root):
    out = []
    for dp, _, fns in os.walk(root):
        for fn in fns:
            p = os.path.join(dp, fn)
            try:
                out.append({"path": p, "sha256": sha(p), "size": os.path.getsize(p)})
            except Exception:
                pass
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="datasets")
    ap.add_argument("--out", default="artifacts/datasets/checksums.json")
    a = ap.parse_args()
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    data = {
        "root": a.root,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "files": scan(a.root),
    }
    json.dump(data, open(a.out, "w"), indent=2)
    print(f"[checksums] wrote {a.out} (files={len(data['files'])})")
