#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import pathlib
import time

DEF_EXTS = {".json", ".csv", ".npz", ".txt", ".png", ".jpg", ".jpeg", ".bin"}


def sha256(p, buf=1024 * 1024):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(buf), b""):
            h.update(chunk)
    return h.hexdigest()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="datasets")
    ap.add_argument("--out", default="datasets/manifest.json")
    ap.add_argument("--max-mb", type=int, default=200)
    ap.add_argument("--exts", nargs="*", default=sorted(DEF_EXTS))
    args = ap.parse_args()
    root = pathlib.Path(args.root)
    root.mkdir(parents=True, exist_ok=True)
    out_abs = pathlib.Path(args.out).resolve()
    max_bytes = args.max_mb * 1024 * 1024
    items = []
    total = 0
    hashed = 0
    for dp, _, files in os.walk(root):
        for fn in files:
            p = (pathlib.Path(dp) / fn).resolve()
            if p == out_abs:  # skip the output manifest itself
                continue
            if args.exts and p.suffix.lower() not in set(args.exts):
                continue
            total += 1
            sz = p.stat().st_size
            rec = {
                "relpath": str(p.relative_to(root.resolve())),
                "bytes": sz,
                "mtime": int(p.stat().st_mtime),
            }
            if sz <= max_bytes:
                rec["sha256"] = sha256(p)
                hashed += 1
            else:
                rec["sha256"] = None
                rec["skipped_size"] = True
            items.append(rec)
    man = {
        "meta": {
            "tool": "datasets/manifest.py",
            "ts": int(time.time()),
            "root": str(root),
            "total": total,
            "hashed": hashed,
            "max_bytes": max_bytes,
            "exts": args.exts,
        },
        "files": items,
    }
    pathlib.Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    json.dump(man, open(args.out, "w"), indent=2, sort_keys=True)
    print(f"[scan] wrote {args.out} (files={total}, hashed={hashed})")


if __name__ == "__main__":
    main()
