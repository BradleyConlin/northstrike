#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json, math
from pathlib import Path

def generate(sim_seconds: float, dt: float):
    n = max(2, int(sim_seconds / dt))
    for i in range(n + 1):
        t = i * dt
        angle = 2 * math.pi * t / sim_seconds if sim_seconds > 0 else 0.0
        x = 5 * math.cos(angle)
        y = 5 * math.sin(angle)
        z = 10.0
        w = 2 * math.pi / sim_seconds if sim_seconds > 0 else 0.0
        vx = -5 * math.sin(angle) * w
        vy =  5 * math.cos(angle) * w
        vz = 0.0
        yield {"t": f"{t:.2f}","x": f"{x:.3f}","y": f"{y:.3f}","z": f"{z:.3f}",
               "vx": f"{vx:.3f}","vy": f"{vy:.3f}","vz": f"{vz:.3f}"}

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim-seconds", type=float, default=2.0)
    ap.add_argument("--dt", type=float, default=0.02)
    ap.add_argument("--wp-radius", type=float, default=0.5)
    args = ap.parse_args()

    outdir = Path("artifacts"); outdir.mkdir(exist_ok=True)
    csv_path = outdir / "waypoint_run.csv"
    with csv_path.open("w", newline="") as f:
        fn = ["t","x","y","z","vx","vy","vz"]
        w = csv.DictWriter(f, fieldnames=fn); w.writeheader()
        for row in generate(args.sim_seconds, args.dt): w.writerow(row)

    metrics = {
        "sim_seconds": float(args.sim_seconds),
        "dt": float(args.dt),
        "wp_radius": float(args.wp_radius),
        "samples": sum(1 for _ in generate(args.sim_seconds, args.dt)),
    }
    (outdir / "waypoint_metrics.json").write_text(json.dumps(metrics, indent=2))
    print(f"Wrote {csv_path} and waypoint_metrics.json")

if __name__ == "__main__":
    main()
