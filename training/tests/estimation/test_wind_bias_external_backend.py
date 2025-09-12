import csv, pathlib, subprocess, sys, textwrap

def _write_min_csvs(dst):
    (dst/"run_000").mkdir(parents=True, exist_ok=True)
    for name, header in {
        "imu.csv": ["t","ax","ay","az","gx","gy","gz"],
        "gnss.csv":["t","lat","lon","alt","horiz_sigma_m"],
        "pose.csv":["t","x","y","z","qw","qx","qy","qz"],
    }.items():
        with (dst/"run_000"/name).open("w", newline="") as f:
            w=csv.writer(f); w.writerow(header)
            w.writerow([0,0,0,0,0,0,0]) if name=="imu.csv" else None
            if name=="gnss.csv": w.writerow([0,0,0,0,1.0])
            if name=="pose.csv": w.writerow([0,0,0,0,1,0,0,0])

def test_external_backend_copy(tmp_path):
    # one-combo sweep to match run_000
    cfg = tmp_path/"sweep.yaml"
    cfg.write_text(textwrap.dedent("""
    sweep:
      seeds: [1]
      wind_speed_mps: [0.0]
      wind_dir_deg: [0]
      gyro_bias_dps: [0.0]
      gnss_bias_m: [0.0]
    """).strip()+"\n")

    src = tmp_path/"src"; _write_min_csvs(src)
    out_dir = tmp_path/"out"
    cmd = [sys.executable, "scripts/estimation/log_synthetic_flights.py",
           "--config", str(cfg), "--out-dir", str(out_dir),
           "--dataset-id","sim_test","--no-mlflow",
           "--write-traces", "--backend","external","--traces-src", str(src)]
    subprocess.run(cmd, check=True, capture_output=True, text=True)

    # verify copy
    base = next(p for p in out_dir.iterdir() if p.is_dir())
    r0 = base/"run_000"
    assert (r0/"imu.csv").is_file()
    assert (r0/"gnss.csv").is_file()
    assert (r0/"pose.csv").is_file()
