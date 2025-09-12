import csv
import os
import subprocess
import sys


def test_depth_offline_smoke(tmp_path):
    model = "artifacts/onnx/depth_e24.onnx"
    assert os.path.isfile(model), "missing artifacts/onnx/depth_e24.onnx"

    out_npz = tmp_path / "depth_out.npz"
    out_csv = tmp_path / "depth_stats.csv"

    subprocess.run(
        [
            sys.executable,
            "scripts/inference/run_depth_offline.py",
            "--model",
            model,
            "--mode",
            "rand",
            "--out-npz",
            str(out_npz),
            "--out-csv",
            str(out_csv),
        ],
        check=True,
    )

    assert out_npz.exists()
    assert out_csv.exists()

    rows = list(csv.reader(open(out_csv)))
    keys = {r[0] for r in rows[1:]}  # skip header
    for k in ("in_shape", "out_shape", "min", "max", "mean", "std"):
        assert k in keys
