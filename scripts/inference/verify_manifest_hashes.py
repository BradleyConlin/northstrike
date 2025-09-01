#!/usr/bin/env python3
import argparse
import hashlib
import json
import pathlib
import sys


def sha256_path(p: pathlib.Path, chunk=1 << 20) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def iter_entries(manifest):
    # supports dict-of-entries or list-of-entries
    if isinstance(manifest, dict):
        for k, v in manifest.items():
            yield k, v
    elif isinstance(manifest, list):
        for i, v in enumerate(manifest):
            name = v.get("name") or v.get("target") or f"idx{i}"
            yield name, v
    else:
        raise TypeError("manifest must be dict or list")


def get_model_path(entry) -> pathlib.Path:
    # prefer dst, else path, else src
    p = entry.get("dst") or entry.get("path") or entry.get("src")
    if not p:
        raise ValueError("entry missing 'dst'/'path'/'src'")
    return pathlib.Path(p)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--check", action="store_true", help="verify sha256 matches")
    ap.add_argument("--write", action="store_true", help="write missing sha256 values")
    args = ap.parse_args()

    manifest_path = pathlib.Path(args.manifest)
    m = json.load(open(manifest_path))
    changed = False
    failures = []

    for name, entry in iter_entries(m):
        p = get_model_path(entry)
        if not p.is_file():
            failures.append((name, "missing", str(p)))
            print(f"[verify] {name}: MISSING file {p}")
            continue
        got = sha256_path(p)
        want = entry.get("sha256")
        if want:
            if got != want:
                failures.append((name, "mismatch", f"{want} != {got}"))
                print(f"[verify] {name}: SHA MISMATCH {want} != {got}")
            else:
                print(f"[verify] {name}: OK {got[:8]}…")
        else:
            if args.write:
                entry["sha256"] = got
                changed = True
                print(f"[verify] {name}: wrote sha256 {got}")
            else:
                failures.append((name, "missing-sha", got))
                print(f"[verify] {name}: sha256 missing (got {got})")

    if changed:
        json.dump(m, open(manifest_path, "w"), indent=2)
        print(f"[verify] updated {manifest_path}")

    if args.check and failures:
        sys.exit(2)
    if not args.check and not args.write:
        # default to check behavior if neither flag given
        sys.exit(0 if not failures else 2)


if __name__ == "__main__":
    main()
