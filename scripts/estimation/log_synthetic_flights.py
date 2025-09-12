#!/usr/bin/env python3
"""
Task 19 — Synthetic flight logger (wind & sensor biases)
Phase 1: JSONL summary + MLflow tags (done)
Phase 2: optional per-run traces (IMU, GNSS, Pose) via --write-traces

Design:
- Reads a sweep YAML (seeds, wind, biases)
- For each combo, writes a JSONL record and, if requested, per-run CSV traces:
    artifacts/logs/estimation/<stamp>/run_XXX/{imu.csv,gnss.csv,pose.csv}
- MLflow logging remains optional and local (file:artifacts/mlruns by default)
- Trace generator is deterministic given seed + params and is a drop-in stub
  to be replaced by SITL; interface stays the same.
"""
from __future__ import annotations
import argparse, itertools, json, math, os, sys, time, pathlib, subprocess, csv, random
from dataclasses import dataclass, asdict

try:
    import yaml  # PyYAML
except Exception:
    print("[warn] PyYAML not available; please add to requirements.txt", file=sys.stderr)
    raise

# ---------- utilities ----------
def _git_sha_short() -> str:
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
        return out or "unknown"
    except Exception:
        return "unknown"

def _now_stamp() -> str:
    return time.strftime("%Y%m%d_%H%M%S", time.localtime())

def _ensure_dir(p: pathlib.Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

# ---------- config schema ----------
@dataclass
class Sweep:
    seeds: list[int]
    wind_speed_mps: list[float]
    wind_dir_deg: list[float]
    gyro_bias_dps: list[float]
    gnss_bias_m: list[float]

@dataclass
class RunParams:
    seed: int
    wind_speed_mps: float
    wind_dir_deg: float
    gyro_bias_dps: float
    gnss_bias_m: float

@dataclass
class RunMetrics:
    wind_u_mps: float
    wind_v_mps: float
    wind_speed_mps: float
    gnss_bias_mag_m: float

def derived_metrics(p: RunParams) -> RunMetrics:
    rad = math.radians(p.wind_dir_deg)
    u = p.wind_speed_mps * math.cos(rad)
    v = p.wind_speed_mps * math.sin(rad)
    return RunMetrics(
        wind_u_mps=round(u, 6),
        wind_v_mps=round(v, 6),
        wind_speed_mps=float(p.wind_speed_mps),
        gnss_bias_mag_m=abs(float(p.gnss_bias_m)),
    )

# ---------- traces (stub; deterministic & fast) ----------
def write_traces(out_dir: pathlib.Path, p: RunParams, steps: int, dt: float) -> None:
    """
    Writes imu.csv, gnss.csv, pose.csv with simple kinematics influenced by wind & biases.
    Columns:
      imu.csv  : t, ax, ay, az, gx, gy, gz
      gnss.csv : t, lat, lon, alt, horiz_sigma_m
      pose.csv : t, x, y, z, qw, qx, qy, qz
    """
    _ensure_dir(out_dir)
    rnd = random.Random(p.seed)
    # Simple planar drift with wind; z fixed at 10 m; yaw follows direction of travel.
    x = y = 0.0
    z = 10.0
    vx = p.wind_speed_mps * math.cos(math.radians(p.wind_dir_deg))
    vy = p.wind_speed_mps * math.sin(math.radians(p.wind_dir_deg))
    yaw = math.atan2(vy, vx) if (vx or vy) else 0.0

    imu_path = out_dir / "imu.csv"
    gnss_path = out_dir / "gnss.csv"
    pose_path = out_dir / "pose.csv"

    with imu_path.open("w", newline="") as f_imu, \
         gnss_path.open("w", newline="") as f_gnss, \
         pose_path.open("w", newline="") as f_pose:
        imu_w = csv.writer(f_imu)
        gnss_w = csv.writer(f_gnss)
        pose_w = csv.writer(f_pose)

        imu_w.writerow(["t", "ax", "ay", "az", "gx", "gy", "gz"])
        gnss_w.writerow(["t", "lat", "lon", "alt", "horiz_sigma_m"])
        pose_w.writerow(["t", "x", "y", "z", "qw", "qx", "qy", "qz"])

        # Origin lat/lon near Toronto; 1 deg lat ~ 111 km; 1 deg lon ~ 78.7 km here
        lat0 = 43.6532
        lon0 = -79.3832
        m_per_deg_lat = 111_000.0
        m_per_deg_lon = 78_700.0

        t = 0.0
        for _ in range(steps):
            # Simple kinematics with tiny random accel
            ax = 0.1 * (rnd.random() - 0.5)
            ay = 0.1 * (rnd.random() - 0.5)
            az = 0.0

            vx += ax * dt
            vy += ay * dt
            x += vx * dt
            y += vy * dt
            yaw = math.atan2(vy, vx + 1e-9)

            # Gyro bias + tiny noise (deg/s)
            gx = p.gyro_bias_dps + 0.02 * (rnd.random() - 0.5)
            gy = 0.02 * (rnd.random() - 0.5)
            gz = 0.02 * (rnd.random() - 0.5)

            imu_w.writerow([round(t, 3), round(ax, 6), round(ay, 6), round(az, 6),
                            round(gx, 6), round(gy, 6), round(gz, 6)])

            # GNSS with horizontal bias (meters) applied along +x; convert to deg
            lat = lat0 + (y + 0.0) / m_per_deg_lat
            lon = lon0 + (x + p.gnss_bias_m) / m_per_deg_lon
            alt = 100.0
            gnss_sigma = 1.5 + abs(p.gnss_bias_m) * 0.1
            gnss_w.writerow([round(t, 3), round(lat, 8), round(lon, 8), alt, round(gnss_sigma, 3)])

            # Pose quaternion from yaw (roll/pitch=0)
            cy = math.cos(yaw * 0.5); sy = math.sin(yaw * 0.5)
            qw, qx, qy, qz = cy, 0.0, 0.0, sy
            pose_w.writerow([round(t, 3), round(x, 4), round(y, 4), z,
                             round(qw, 6), qx, qy, round(qz, 6)])

            t += dt

# ---------- mlflow (optional) ----------
class MLflowClient:
    def __init__(self, enabled: bool, experiment: str):
        self.enabled = enabled
        self.experiment = experiment
        self.mlflow = None
        if enabled:
            try:
                import mlflow  # lazy import
                self.mlflow = mlflow
                import os, pathlib
                uri = os.environ.get("MLFLOW_TRACKING_URI", "file:artifacts/mlruns")
                if uri.startswith("file:"):
                    mlruns_path = pathlib.Path(uri.split("file:")[-1])
                    mlruns_path.mkdir(parents=True, exist_ok=True)
                mlflow.set_tracking_uri(uri)
                mlflow.set_experiment(experiment)
            except Exception as e:
                print(f"[warn] MLflow disabled ({e})", file=sys.stderr)
                self.enabled = False

    def log(self, name: str, params: dict, metrics: dict, tags: dict) -> str:
        if not self.enabled:
            return "no-mlflow"
        with self.mlflow.start_run(run_name=name) as r:
            self.mlflow.log_params(params)
            self.mlflow.log_metrics(metrics)
            self.mlflow.set_tags(tags)
            return r.info.run_id

# ---------- main ----------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True, help="YAML sweep file")
    ap.add_argument("--out-dir", default="artifacts/logs/estimation", help="base output dir")
    ap.add_argument("--dataset-id", default=None, help="dataset id tag")
    ap.add_argument("--experiment", default="northstrike", help="MLflow experiment name")
    ap.add_argument("--no-mlflow", action="store_true", help="disable MLflow logging")

    # Phase 2: trace options
    ap.add_argument("--write-traces", action="store_true", help="emit IMU/GNSS/Pose CSVs per run")
    ap.add_argument("--steps", type=int, default=200, help="trace length (rows)")
    ap.add_argument("--dt", type=float, default=0.02, help="timestep in seconds")

    args = ap.parse_args()

    cfg = yaml.safe_load(pathlib.Path(args.config).read_text())
    sw = Sweep(**cfg["sweep"])
    dsid = args.dataset_id or f"sim_sweep_{time.strftime('%F')}"

    out_base = pathlib.Path(args.out_dir) / f"task19_{_now_stamp()}"
    _ensure_dir(out_base)
    out_jsonl = out_base / "runs.jsonl"
    out_summary = out_base / "sweep_summary.json"

    mlf = MLflowClient(enabled=(not args.no_mlflow), experiment=args.experiment)
    git_sha = _git_sha_short()

    combos = itertools.product(
        sw.seeds, sw.wind_speed_mps, sw.wind_dir_deg, sw.gyro_bias_dps, sw.gnss_bias_m
    )

    n = 0
    run_dirs = []
    with out_jsonl.open("w") as f:
        for seed, spd, deg, gyro_b, gnss_b in combos:
            p = RunParams(seed=seed, wind_speed_mps=spd, wind_dir_deg=deg,
                          gyro_bias_dps=gyro_b, gnss_bias_m=gnss_b)
            m = derived_metrics(p)
            run_name = f"task19_s{seed}_w{spd}_d{deg}_gnss{gnss_b}_gyro{gyro_b}"
            tags = {
                "task": "19",
                "component": "estimation_logging",
                "git_sha": git_sha,
                "dataset_id": dsid,
                "seed": str(seed),
            }
            params = {k: float(v) if isinstance(v, (int, float)) else v for k, v in asdict(p).items()}
            metrics = asdict(m)

            run_id = mlf.log(run_name, params, metrics, tags)

            # Optional traces per run
            rdir = out_base / f"run_{n:03d}"
            if args.write_traces:
                write_traces(rdir, p, steps=args.steps, dt=args.dt)
            run_dirs.append(str(rdir))

            record = {
                "run_id": run_id,
                "name": run_name,
                "params": params,
                "metrics": metrics,
                "tags": tags,
                "run_dir": str(rdir),
            }
            f.write(json.dumps(record) + "\n")
            n += 1

    summary = {
        "n_runs": n,
        "out_dir": str(out_base),
        "git_sha": git_sha,
        "dataset_id": dsid,
        "config": cfg,
        "run_dirs": run_dirs,
        "traces": bool(args.write_traces),
        "steps": int(args.steps),
        "dt": float(args.dt),
    }
    out_summary.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"[task19] wrote {n} runs → {out_base}")

if __name__ == "__main__":
    main()
