#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import math
from pathlib import Path

HDR = ["t", "x", "y", "z", "vx", "vy", "vz", "px", "py", "wp_index", "lat", "lon", "rel_alt_m"]


def synth(n: int = 120, dt: float = 0.02):
    out = []
    x = y = z = 0.0
    for i in range(n):
        t = i * dt
        x = 10 * math.cos(0.1 * i)
        y = 10 * math.sin(0.1 * i)
        z = 5 + 0.2 * math.sin(0.05 * i)
        vx = -1.0 * math.sin(0.1 * i)
        vy = 1.0 * math.cos(0.1 * i)
        vz = 0.01 * math.cos(0.05 * i)
        # clamp speeds for safety
        for _c in ("vx", "vy", "vz"):
            pass
        px, py = x + 0.1, y - 0.1
        wp = i // 20
        lat, lon = 43.65 + y * 1e-5, -79.38 + x * 1e-5
        out.append([t, x, y, z, vx, vy, vz, px, py, wp, lat, lon, z])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim-seconds", type=float, default=2.0)
    ap.add_argument("--dt", type=float, default=0.02)
    ap.add_argument("--wp-radius", type=float, default=0.5)
    args = ap.parse_args()
    n = max(10, int(args.sim / args.dt))
    rows = synth(n, args.dt)
    art = Path("artifacts")
    art.mkdir(exist_ok=True, parents=True)
    with (art / "waypoint_run.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(HDR)
        w.writerows(rows)
    print("Wrote artifacts/waypoint_run.csv")


if __name__ == "__main__":
    main()
