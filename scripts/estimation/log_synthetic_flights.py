#!/usr/bin/env python3
"""
Task 19 — Synthetic flight logger (wind & sensor biases)

- Reads a sweep config YAML (seeds, wind, biases)
- Generates combinations and logs:
  * params (seed, wind, dir, biases)
  * simple derived metrics (wind_u, wind_v, bias_mag)
- Writes JSONL (one line per run) + sweep_summary.json
- Optionally logs to MLflow experiment "northstrike" with tags.

Designed to be cheap and deterministic. No simulator dependency yet.
"""
from __future__ import annotations
import argparse, itertools, json, math, os, sys, time, pathlib, subprocess
from dataclasses import dataclass, asdict

try:
    import yaml  # PyYAML
except Exception as e:  # pragma: no cover
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
    with out_jsonl.open("w") as f:
        for seed, spd, deg, gyro_b, gnss_b in combos:
            p = RunParams(seed=seed, wind_speed_mps=spd, wind_dir_deg=deg,
                          gyro_bias_dps=gyro_b, gnss_bias_m=gnss_b)
            m = derived_metrics(p)
            run_name = f"task19_s{seed}_w{spd}_d{deg}_g{gnss_b}_gyro{gyro_b}"

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
            record = {
                "run_id": run_id,
                "name": run_name,
                "params": params,
                "metrics": metrics,
                "tags": tags,
            }
            f.write(json.dumps(record) + "\n")
            n += 1

    summary = {
        "n_runs": n,
        "out_dir": str(out_base),
        "git_sha": git_sha,
        "dataset_id": dsid,
        "config": cfg,
    }
    out_summary.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"[task19] wrote {n} runs → {out_base}")

if __name__ == "__main__":
    main()
