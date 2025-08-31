#!/usr/bin/env python3
import argparse
import json
import pathlib
import zipfile
from typing import List


def _load_manifest(p: pathlib.Path):
    m = json.loads(p.read_text())
    return list(m.values()) if isinstance(m, dict) else m


def _model_paths(items) -> List[pathlib.Path]:
    out = []
    for it in items:
        p = it.get("dst") or it.get("path")
        if p:
            out.append(pathlib.Path(p))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default="deploy/models/manifest.json")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    man = pathlib.Path(args.manifest)
    items = _load_manifest(man)
    paths = _model_paths(items)
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(man, "manifest.json")
        for p in paths:
            z.write(p, f"models/{p.name}")
    print(f"[pack] wrote {out} (files={len(paths)})")


if __name__ == "__main__":
    main()
