#!/usr/bin/env python3
import argparse
import hashlib
import json
import pathlib
import time

import onnx
import onnxruntime as ort

DEF_MAN = "deploy/models/manifest.json"
DEF_OUT = "artifacts/releases/integrity_summary.json"


def sha256(path, buf=1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(buf), b""):
            h.update(chunk)
    return h.hexdigest()


def iter_manifest(man):
    # support dict {"name": {...}} or list [{"path": ...}, ...]
    if isinstance(man, dict):
        for name, rec in man.items():
            yield name, rec
    elif isinstance(man, list):
        for i, rec in enumerate(man):
            name = rec.get("name") or f"model[{i}]"
            yield name, rec


def infer_io_and_opset(p):
    # Use ORT for IO shapes and ONNX for opset
    sess = ort.InferenceSession(str(p), providers=["CPUExecutionProvider"])
    ins = [
        {
            "name": x.name,
            "dtype": x.type,
            "shape": [d if isinstance(d, int) else (d if d is None else str(d)) for d in x.shape],
        }
        for x in sess.get_inputs()
    ]
    outs = [
        {
            "name": x.name,
            "dtype": x.type,
            "shape": [d if isinstance(d, int) else (d if d is None else str(d)) for d in x.shape],
        }
        for x in sess.get_outputs()
    ]
    m = onnx.load(str(p))
    opset = max((oi.version for oi in m.opset_import), default=None)
    return ins, outs, opset


def try_load_json(p):
    try:
        return json.load(open(p))
    except Exception:
        return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifest", default=DEF_MAN)
    ap.add_argument("--out", default=DEF_OUT)
    args = ap.parse_args()

    man = json.load(open(args.manifest))
    outp = pathlib.Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)

    # optional perf artifacts (best-effort)
    perf_dir = pathlib.Path("artifacts/perf")
    perf = {
        "perception_depth_profile": try_load_json(perf_dir / "perception_depth.json"),
        "control_policy_profile": try_load_json(perf_dir / "control_policy.json"),
        "e2e_tick": try_load_json(perf_dir / "e2e_tick.json"),
    }

    models = {}
    for name, rec in iter_manifest(man):
        p = pathlib.Path(rec.get("dst") or rec.get("path") or "")
        if not p.is_file():
            models[name] = {"error": f"missing file: {p}"}
            continue
        size = p.stat().st_size
        mtime = int(p.stat().st_mtime)
        file_sha = sha256(p)
        # Pull sha from manifest if present (plus we keep computed)
        declared_sha = rec.get("sha256")

        inputs, outputs, opset = infer_io_and_opset(p)

        models[name] = {
            "path": str(p),
            "bytes": size,
            "mtime": mtime,
            "sha256_computed": file_sha,
            "sha256_manifest": declared_sha,
            "opset": opset,
            "inputs": inputs,
            "outputs": outputs,
        }

    summary = {
        "meta": {
            "tool": "scripts/inference/integrity_summary.py",
            "ts": int(time.time()),
            "manifest": args.manifest,
        },
        "models": models,
        "perf": perf,
    }

    json.dump(summary, open(outp, "w"), indent=2, sort_keys=True)
    print(f"[integrity] wrote {outp}  (models={len(models)})")
    # simple guard: ensure computed sha == manifest sha if present
    bad = []
    for k, v in models.items():
        if (
            "sha256_manifest" in v
            and v["sha256_manifest"]
            and v["sha256_manifest"] != v["sha256_computed"]
        ):
            bad.append(k)
    if bad:
        print("[integrity] WARNING: sha mismatch for:", ", ".join(bad))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
