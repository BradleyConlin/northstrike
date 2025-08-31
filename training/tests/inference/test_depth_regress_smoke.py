import json
import pathlib
import subprocess
import sys

M = "artifacts/onnx/depth_e24.onnx"
B = "artifacts/perf/depth_regress_baseline.json"


def _run(args):
    r = subprocess.run([sys.executable, *args], check=True, capture_output=True, text=True)
    return r.stdout


def test_depth_regress_roundtrip(tmp_path):
    pathlib.Path("artifacts/perf").mkdir(parents=True, exist_ok=True)
    _run(["scripts/inference/depth_regress.py", "--model", M, "--out-json", B])
    _run(["scripts/inference/depth_regress.py", "--model", M, "--check-against", B])
