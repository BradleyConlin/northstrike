#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, subprocess, sys
from pathlib import Path

def movavg(a, k=5):
    out=[]; s=0.0
    for i,v in enumerate(a):
        s += v
        if i >= k: s -= a[i-k]
        out.append(s / (k if i+1>k else i+1))
    return out

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim-seconds", type=float, default=2.0)
    ap.add_argument("--dt", type=float, default=0.02)
    ap.add_argument("--wp-radius", type=float, default=0.5)
    a = ap.parse_args()

    raw = Path("artifacts/waypoint_run.csv")
    if not raw.exists():
        subprocess.run([sys.executable, "-m", "scripts.run_waypoint_demo",
                        "--sim-seconds", str(a.sim_seconds),
                        "--dt", str(a.dt),
                        "--wp-radius", str(a.wp_radius)], check=True)

    rows = list(csv.DictReader(raw.open()))
    t  = [r["t"] for r in rows]
    x  = [float(r["x"])  for r in rows];  y  = [float(r["y"])  for r in rows]
    z  = [float(r.get("z","10.0")) for r in rows]
    vx = [float(r["vx"]) for r in rows];  vy = [float(r["vy"]) for r in rows]
    vz = [float(r.get("vz","0.0")) for r in rows]
    ex, ey = movavg(x), movavg(y); svx, svy = movavg(vx), movavg(vy)

    out = Path("artifacts/waypoint_run_ekf.csv")
    fn = ["t","x","y","z","vx","vy","vz","px","py","ekf_px","ekf_py","lat","lon","rel_alt_m","wp_index"]
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fn); w.writeheader()
        for i in range(len(rows)):
            w.writerow({
                "t": t[i], "x": f"{x[i]:.3f}", "y": f"{y[i]:.3f}", "z": f"{z[i]:.3f}",
                "vx": f"{svx[i]:.3f}", "vy": f"{svy[i]:.3f}", "vz": f"{vz[i]:.3f}",
                "px": f"{x[i]:.3f}", "py": f"{y[i]:.3f}",
                "ekf_px": f"{ex[i]:.3f}", "ekf_py": f"{ey[i]:.3f}",
                "lat": "0.000000", "lon": "0.000000", "rel_alt_m": "10.000",
                "wp_index": "0",
            })
    print(f"Wrote {out}")

if __name__ == "__main__":
    main()
