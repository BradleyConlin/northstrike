#!/usr/bin/env python3
import argparse
import json
import time
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="deploy/models/manifest.json")
    ap.add_argument("--target", required=True)
    ap.add_argument("--out", default="artifacts/releases/registry.json")
    a = ap.parse_args()
    m = json.load(open(a.manifest))
    e = m.get(a.target) or {}
    rec = {
        "target": a.target,
        "src": e.get("src"),
        "sha256": e.get("sha256"),
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    db = []
    if Path(a.out).exists():
        try:
            db = json.load(open(a.out))
        except:
            db = []
    db.append(rec)
    json.dump(db, open(a.out, "w"), indent=2)
    print(f"[registry] appended {a.target} ({(rec['sha256'] or '')[:8]}…) to {a.out}")


if __name__ == "__main__":
    main()
