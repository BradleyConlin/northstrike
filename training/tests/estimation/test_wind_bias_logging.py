import json
import pathlib
import subprocess
import sys
import textwrap


def test_wind_bias_logging(tmp_path):
    # write a tiny sweep to keep runtime low
    cfg = tmp_path / "sweep.yaml"
    cfg.write_text(
        textwrap.dedent(
            """
    sweep:
      seeds: [1, 2]
      wind_speed_mps: [0.0, 5.0]
      wind_dir_deg: [0, 180]
      gyro_bias_dps: [0.0, 0.05]
      gnss_bias_m: [0.0, 1.5]
    """
        ).strip()
        + "\n"
    )

    out_dir = tmp_path / "out"
    cmd = [
        sys.executable,
        "scripts/estimation/log_synthetic_flights.py",
        "--config",
        str(cfg),
        "--out-dir",
        str(out_dir),
        "--dataset-id",
        "sim_test",
        "--no-mlflow",
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)

    # find produced folder
    base = pathlib.Path(out_dir)
    subdirs = [p for p in base.iterdir() if p.is_dir()]
    assert subdirs, "no output subdir created"
    odir = subdirs[0]
    runs = odir / "runs.jsonl"
    summ = odir / "sweep_summary.json"

    assert runs.is_file(), "missing runs.jsonl"
    assert summ.is_file(), "missing sweep_summary.json"

    lines = runs.read_text().strip().splitlines()
    # 2*2*2*2*2 = 32 combos
    assert len(lines) == 32, f"expected 32 runs, got {len(lines)}"

    rec0 = json.loads(lines[0])
    for k in ("params", "metrics", "tags"):
        assert k in rec0
