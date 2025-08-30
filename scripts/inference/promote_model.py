#!/usr/bin/env python3
import argparse, hashlib, json, os, sys, time
from pathlib import Path
from typing import Any, Dict, Tuple

import onnxruntime as ort
import yaml


def _flatten_targets(d: Dict[str, Any], prefix: str = "") -> Dict[str, Dict[str, Any]]:
    out = {}
    if isinstance(d, dict):
        if {"path", "shape"} <= set(d.keys()):
            out[prefix.strip(".")] = d
        else:
            for k, v in d.items():
                out.update(_flatten_targets(v, f"{prefix}.{k}" if prefix else k))
    return out


def _load_budgets(path: str) -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    cfg = yaml.safe_load(Path(path).read_text())
    roots = cfg.get("targets", cfg)  # support either top-level or targets:
    flat = _flatten_targets(roots)
    return flat, cfg


def _sha256(p: Path, block=1024 * 1024) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        while True:
            b = f.read(block)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def _check_input_shape(sess: ort.InferenceSession, want: str) -> Tuple[bool, str, str]:
    got_dims = [int(x) for x in sess.get_inputs()[0].shape]
    got = "x".join(str(x) for x in got_dims)
    ok = (got == want.replace(" ", ""))
    return ok, got, want


def _ensure_symlink(dst_path: Path, src_abs: Path):
    dst_path.parent.mkdir(parents=True, exist_ok=True)
    if dst_path.exists() or dst_path.is_symlink():
        # backup non-symlink once
        if not dst_path.is_symlink():
            bak = dst_path.with_suffix(dst_path.suffix + f".bak-{int(time.time())}")
            dst_path.replace(bak)
        else:
            try:
                dst_path.unlink()
            except FileNotFoundError:
                pass
    os.symlink(src_abs, dst_path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="docs/perf/budgets.yaml")
    ap.add_argument("--target", required=True, help="e.g. perception.depth or control.policy")
    ap.add_argument("--model", required=True, help="source .onnx to promote")
    ap.add_argument("--provider", default="CPUExecutionProvider")
    ap.add_argument("--manifest", default="deploy/models/manifest.json")
    args = ap.parse_args()

    flat, _cfg = _load_budgets(args.config)
    if args.target not in flat:
        print(f"[error] target {args.target} not found in {args.config}", file=sys.stderr)
        sys.exit(2)

    tgt = flat[args.target]
    want_shape = str(tgt["shape"]).lower().replace(" ", "")
    dst = Path(str(tgt["path"]))
    src = Path(args.model).resolve()

    if not src.is_file():
        print(f"[error] source model {src} not found", file=sys.stderr)
        sys.exit(2)

    # validate source model input shape
    sess = ort.InferenceSession(str(src), providers=[args.provider])
    ok, got, want = _check_input_shape(sess, want_shape)
    if not ok:
        print(f"[error] input shape mismatch for {args.target}: got={got} want={want}", file=sys.stderr)
        sys.exit(3)

    # promote (symlink)
    _ensure_symlink(dst, src)

    # update manifest
    man_path = Path(args.manifest)
    man_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {}
    if man_path.exists():
        try:
            manifest = json.loads(man_path.read_text() or "{}")
        except Exception:
            manifest = {}
    manifest[args.target] = {
        "dst": str(dst),
        "src": str(src),
        "sha256": _sha256(src),
        "validated_shape": got,
        "ts": int(time.time()),
    }
    man_path.write_text(json.dumps(manifest, indent=2))

    print(f"[promote] {args.target} -> {dst} ⇒ {src.name}  shape={got}  OK")
    print(f"[manifest] {args.manifest} updated")


if __name__ == "__main__":
    main()
