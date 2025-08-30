import json, shutil, subprocess, sys
from pathlib import Path
import yaml

CFG = "docs/perf/budgets.yaml"
MAN = "deploy/models/manifest.json"

def _run(cmd):
    return subprocess.run(cmd, check=True, capture_output=True, text=True).stdout

def _target_path(cfg: dict, dotted: str) -> Path:
    roots = cfg.get("targets", cfg)
    def flat(d, prefix=""):
        out = {}
        if isinstance(d, dict):
            if "path" in d and "shape" in d:
                out[prefix] = d
            else:
                for k, v in d.items():
                    key = f"{prefix}.{k}" if prefix else k
                    out.update(flat(v, key))
        return out
    f = flat(roots)
    assert dotted in f, f"target '{dotted}' not found in budgets"
    return Path(f[dotted]["path"])

def test_promote_policy_symlink_and_manifest(tmp_path):
    src = Path("artifacts/onnx/policy_copy.onnx")
    shutil.copyfile("artifacts/onnx/policy_dummy.onnx", src)
    _run([sys.executable, "scripts/inference/promote_model.py",
          "--config", CFG, "--target", "control.policy", "--model", str(src)])

    cfg = yaml.safe_load(open(CFG))
    dst = _target_path(cfg, "control.policy")
    assert dst.exists()
    if dst.is_symlink():
        assert dst.resolve() == src.resolve()

    d = json.loads(open(MAN).read())
    e = d["control.policy"]
    assert e["validated_shape"] == "1x64"
    assert Path(e["src"]).resolve() == src.resolve()
