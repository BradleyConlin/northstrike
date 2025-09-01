#!/usr/bin/env python3
import hashlib
import json
import os
import sys

MANIFEST = "deploy/models/manifest.json"
DEPTH_NAME = "perception.depth"
DEPTH_PATH = "artifacts/onnx/depth_e24.onnx"
POLICY_NAME = "control.policy"
POLICY_PATH = "artifacts/onnx/policy_dummy.onnx"


def sha256(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def ensure_list_entry(lst, name, path):
    e = next((e for e in lst if e.get("name") == name), None)
    if e is None:
        e = {"name": name, "path": path, "sha256": sha256(path)}
        lst.append(e)
    else:
        e["path"] = path
        e["sha256"] = sha256(path)
    return lst


def ensure_nested_entry(dct, dotted, path):
    parts = dotted.split(".")
    cur = dct
    for p in parts[:-1]:
        cur = cur.setdefault(p, {})
    leaf = cur.setdefault(parts[-1], {})
    # preserve other fields but enforce path + sha256
    leaf["path"] = path
    leaf["sha256"] = sha256(path)
    return dct


def main():
    if not os.path.exists(MANIFEST):
        print(f"[ERR] missing {MANIFEST}", file=sys.stderr)
        sys.exit(2)
    with open(MANIFEST) as f:
        data = json.load(f)

    if isinstance(data, list):
        data = ensure_list_entry(data, DEPTH_NAME, DEPTH_PATH)
        data = ensure_list_entry(data, POLICY_NAME, POLICY_PATH)
    elif isinstance(data, dict):
        data = ensure_nested_entry(data, DEPTH_NAME, DEPTH_PATH)
        data = ensure_nested_entry(data, POLICY_NAME, POLICY_PATH)
    else:
        print("[ERR] unsupported manifest format", file=sys.stderr)
        sys.exit(3)

    with open(MANIFEST, "w") as f:
        json.dump(data, f, indent=2, sort_keys=True)
    print(
        "[OK] manifest repaired:",
        f"\n  {DEPTH_NAME} -> {DEPTH_PATH}",
        f"\n  {POLICY_NAME} -> {POLICY_PATH}",
    )


if __name__ == "__main__":
    main()
