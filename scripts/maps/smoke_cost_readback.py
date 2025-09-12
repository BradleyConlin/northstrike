#!/usr/bin/env python3
import csv
import json
import math
import os
import random
import subprocess
import time


def sh(cmd: str) -> str:
    return subprocess.check_output(cmd, shell=True, text=True)


def main():
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--cost", required=True, help="Float32 cost GeoTIFF (planner source)")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    random.seed(args.seed)

    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    info = json.loads(sh(f'gdalinfo -json "{args.cost}"'))
    # Pull lon/lat bbox
    if "cornerCoordinates" in info:
        corners = info["cornerCoordinates"]
        xs = [corners[k][0] for k in corners]
        ys = [corners[k][1] for k in corners]
    else:
        coords = info["wgs84Extent"]["coordinates"][0]
        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]
    west, east = min(xs), max(xs)
    south, north = min(ys), max(ys)

    rows = []
    for i in range(args.n):
        lon = random.uniform(west, east)
        lat = random.uniform(south, north)
        try:
            val = sh(f'gdallocationinfo -valonly -geoloc "{args.cost}" {lon} {lat}').strip()
            val_f = float(val)
            nodata = False
        except subprocess.CalledProcessError:
            val_f = float("nan")
            nodata = True
        rows.append(dict(i=i, lon=lon, lat=lat, cost=val_f, nodata=nodata))

    with open(args.out, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["i", "lon", "lat", "cost", "nodata"])
        w.writeheader()
        w.writerows(rows)

    ok = [r for r in rows if not (math.isnan(r["cost"]) or r["nodata"])]
    summary = dict(
        samples=args.n,
        valid=len(ok),
        nan=len(rows) - len(ok),
        min=min((r["cost"] for r in ok), default=float("nan")),
        max=max((r["cost"] for r in ok), default=float("nan")),
        mean=(sum(r["cost"] for r in ok) / len(ok) if ok else float("nan")),
        ts=int(time.time()),
    )
    sum_path = os.path.splitext(args.out)[0] + "_summary.json"
    with open(sum_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"Wrote {args.out}")
    print(f"Summary: {sum_path}")


if __name__ == "__main__":
    main()
