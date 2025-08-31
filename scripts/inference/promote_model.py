#!/usr/bin/env python3
import argparse, json, hashlib, sys
from pathlib import Path
import yaml

try:
    import onnxruntime as ort
except Exception:
    ort = None

def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()

def load_yaml(p: Path) -> dict:
    if not p.exists():
        return {}
    with p.open("r") as f:
        return yaml.safe_load(f) or {}

def get_cfg_target(cfg: dict, dotted_key: str) -> dict:
    """Graceful lookup: return {} if any segment is missing."""
    cur = cfg.get("targets")
    if not isinstance(cur, dict):
        return {}
    for part in dotted_key.split("."):
        nxt = cur.get(part)
        if not isinstance(nxt, dict):
            return {}
        cur = nxt
    return cur

def pick_dest(entry_dict: dict, cfg_target: dict) -> str | None:
    """Prefer YAML dst→path→src, else manifest dst→path→src."""
    for k in ("dst", "path", "src"):
        v = cfg_target.get(k)
        if v: return v
    if isinstance(entry_dict, dict):
        for k in ("dst", "path", "src"):
            v = entry_dict.get(k)
            if v: return v
    return None

def link_or_copy(src: Path, dst: Path) -> bool:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        dst.unlink()
    try:
        dst.symlink_to(src.resolve())
        return True
    except Exception:
        dst.write_bytes(src.read_bytes())
        return False

def shape_to_str(shape) -> str:
    dims = []
    for d in shape or []:
        if isinstance(d, int):
            dims.append(str(d))
        else:
            dims.append("?")
    return "x".join(dims) if dims else "?"

def infer_input_shape(model_path: Path) -> str:
    if ort is None:
        return "?"
    sess = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
    ins = sess.get_inputs()
    return shape_to_str(ins[0].shape) if ins else "?"

def read_manifest(path: Path) -> dict:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text())
    # Already dotted dict?
    if isinstance(raw, dict) and all(isinstance(k, str) and "." in k for k in raw.keys()):
        return raw
    # Nested dict under 'targets'
    if isinstance(raw, dict) and "targets" in raw:
        out = {}
        def walk(prefix, node):
            for k, v in node.items():
                if isinstance(v, dict) and any(isinstance(vv, dict) for vv in v.values()):
                    walk(f"{prefix}.{k}" if prefix else k, v)
                else:
                    out[f"{prefix+'.' if prefix else ''}{k}"] = v
        walk("", raw["targets"])
        return out
    # List form
    if isinstance(raw, list):
        out = {}
        for e in raw:
            name = e.get("target") or e.get("name") or e.get("key")
            if name:
                out[str(name)] = {k: v for k, v in e.items() if k not in ("target", "name", "key")}
        return out
    # Fallback
    return raw if isinstance(raw, dict) else {}

def write_manifest(path: Path, dotted: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(dotted, indent=2, sort_keys=True))

def main():
    ap = argparse.ArgumentParser(description="Promote a model to a target and update manifest.")
    ap.add_argument("--config", required=True, help="YAML config (e.g., docs/perf/budgets.yaml)")
    ap.add_argument("--target", required=True, help="Dotted target key, e.g. control.policy")
    ap.add_argument("--model", required=True, help="Path to the ONNX model to promote")
    ap.add_argument("--manifest", default="deploy/models/manifest.json", help="Dotted-keys manifest JSON")
    args = ap.parse_args()

    cfg = load_yaml(Path(args.config))
    cfg_t = get_cfg_target(cfg, args.target)

    src = Path(args.model).resolve()
    if not src.exists():
        print(f"[error] model not found: {src}", file=sys.stderr); sys.exit(2)

    manifest_path = Path(args.manifest)
    manifest = read_manifest(manifest_path)
    entry = manifest.get(args.target, {})

    dest_str = pick_dest(entry, cfg_t)
    if not dest_str:
        # Sensible fallback under artifacts if both YAML & manifest lack a path
        default_name = args.target.replace(".", "_") + ".onnx"
        dest_str = f"artifacts/onnx/{default_name}"
    dst = Path(dest_str)

    was_symlink = link_or_copy(src, dst)

    validated_shape = infer_input_shape(src)
    digest = sha256_file(src)

    # Ensure entry exists
    manifest.setdefault(args.target, {})
    # Always write src/sha/shape; keep a dst field for visibility
    manifest[args.target]["src"] = str(src)
    manifest[args.target]["sha256"] = digest
    manifest[args.target]["validated_shape"] = validated_shape
    manifest[args.target]["dst"] = str(dst)

    write_manifest(manifest_path, manifest)

    mode = "symlink" if was_symlink else "copy"
    print(f"[promote] {args.target} -> {dst} ({mode})")
    print(f"[promote] src={src}")
    print(f"[promote] sha256={digest}")
    print(f"[promote] validated_shape={validated_shape}")

if __name__ == "__main__":
    main()
