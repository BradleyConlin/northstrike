import csv
import os
import subprocess
import sys


def test_policy_offline_smoke(tmp_path):
    incsv = tmp_path / "in.csv"
    with open(incsv, "w", newline="") as f:
        f.write("t," + ",".join([f"f{i}" for i in range(12)]) + "\n")
        f.write("0.00," + ",".join(["0"] * 12) + "\n")
        f.write("0.02," + ",".join(["0"] * 12) + "\n")
        f.write("0.04," + ",".join(["0"] * 12) + "\n")

    outcsv = tmp_path / "out.csv"
    model = "artifacts/onnx/policy_dummy.onnx"
    assert os.path.isfile(model), "missing artifacts/onnx/policy_dummy.onnx"

    subprocess.run(
        [
            sys.executable,
            "scripts/inference/run_policy_offline.py",
            "--model",
            model,
            "--in-csv",
            str(incsv),
            "--out-csv",
            str(outcsv),
        ],
        check=True,
    )

    assert outcsv.exists()
    rows = list(csv.DictReader(open(outcsv)))
    assert len(rows) >= 3
    for r in rows:
        for k in ("u0", "u1", "u2", "u3"):
            assert k in r
