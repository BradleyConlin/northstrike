import csv
import pathlib
import subprocess
import sys
import textwrap


def test_wind_bias_traces(tmp_path):
    cfg = tmp_path / "sweep.yaml"
    cfg.write_text(
        textwrap.dedent(
            """
    sweep:
      seeds: [7]
      wind_speed_mps: [3.0]
      wind_dir_deg: [90]
      gyro_bias_dps: [0.01]
      gnss_bias_m: [1.0]
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
        "--write-traces",
        "--steps",
        "10",
        "--dt",
        "0.05",
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)

    # locate run folder
    base = pathlib.Path(out_dir)
    subdirs = [p for p in base.iterdir() if p.is_dir()]
    assert subdirs, "no output subdir"
    odir = subdirs[0]  # task19_<stamp>
    run_dirs = [p for p in odir.iterdir() if p.is_dir() and p.name.startswith("run_")]
    assert run_dirs, "no run_* folder created"
    r0 = run_dirs[0]

    # check CSVs + headers + row count
    imu = r0 / "imu.csv"
    gnss = r0 / "gnss.csv"
    pose = r0 / "pose.csv"
    for p in (imu, gnss, pose):
        assert p.is_file(), f"missing {p.name}"

    with imu.open() as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["t", "ax", "ay", "az", "gx", "gy", "gz"]
    assert len(rows) == 11  # header + 10 rows

    with gnss.open() as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["t", "lat", "lon", "alt", "horiz_sigma_m"]
    assert len(rows) == 11

    with pose.open() as f:
        rows = list(csv.reader(f))
    assert rows[0] == ["t", "x", "y", "z", "qw", "qx", "qy", "qz"]
    assert len(rows) == 11
