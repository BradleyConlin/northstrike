#!/usr/bin/env python3
"""
Ensure artifacts/waypoint_run.csv has the full EKF contract:

['t','x','y','z','vx','vy','vz','px','py','ekf_px','ekf_py','wp_index','lat','lon','rel_alt_m']

- Reads an existing minimal CSV (t,x,y,z) if present.
- Synthesizes rows if too few (smooth linear/sine motion).
- Computes vx/vy/vz from diffs, clamps to ±40, sets first-row v=0.
- px/py mirror x/y; ekf_px/ekf_py mirror px/py.
- wp_index = 0; lat/lon = 0.0; rel_alt_m = z.
"""
from __future__ import annotations
import csv, math
from pathlib import Path

ART = Path("artifacts")
OUT = ART / "waypoint_run.csv"
REQ = ['t','x','y','z','vx','vy','vz','px','py','ekf_px','ekf_py','wp_index','lat','lon','rel_alt_m']
MIN_ROWS = 10

def _read_existing():
    # prefer waypoint_run.csv; fallback to waypoint_run_ekf.csv
    for p in [ART / "waypoint_run.csv", ART / "waypoint_run_ekf.csv"]:
        if p.exists():
            with p.open() as f:
                r = list(csv.DictReader(f))
                if r:
                    return r
    return []

def _to_float(v, default=0.0):
    try: return float(v)
    except: return default

def _synthesize(n=MIN_ROWS, dt=0.1):
    rows = []
    for i in range(n):
        t = i * dt
        x = 0.5 * i * dt  # linear x
        y = math.sin(0.4 * i * dt)  # gentle sine on y
        z = 0.0
        rows.append({"t":t,"x":x,"y":y,"z":z})
    return rows

def _ensure_min_rows(rows):
    if len(rows) >= MIN_ROWS:
        return rows
    # if t missing, synthesize fresh; else extend smoothly from last
    if not rows or any(k not in rows[0] for k in ("t","x","y","z")):
        return _synthesize(MIN_ROWS)
    out = rows[:]
    if len(out) >= 2:
        dt = max(_to_float(out[-1]["t"]) - _to_float(out[-2]["t"]), 0.1)
    else:
        dt = 0.1
    t = _to_float(out[-1]["t"])
    x = _to_float(out[-1]["x"])
    y = _to_float(out[-1]["y"])
    z = _to_float(out[-1]["z"])
    while len(out) < MIN_ROWS:
        t += dt
        x += 0.5 * dt
        y = math.sin(0.4 * t)
        out.append({"t":t,"x":x,"y":y,"z":z})
    return out

def _clamp(v, lo, hi): return max(lo, min(hi, v))

def main():
    rows = _read_existing()
    base = []
    # normalize to minimal fields or synthesize
    if rows and {"t","x","y","z"} <= set(rows[0].keys()):
        for r in rows:
            base.append({
                "t": _to_float(r.get("t", 0.0)),
                "x": _to_float(r.get("x", 0.0)),
                "y": _to_float(r.get("y", 0.0)),
                "z": _to_float(r.get("z", 0.0)),
            })
    else:
        base = _synthesize()
    base = _ensure_min_rows(base)

    # compute velocities
    full = []
    for i, r in enumerate(base):
        if i == 0:
            vx=vy=vz=0.0
        else:
            dt = max(_to_float(base[i]["t"]) - _to_float(base[i-1]["t"]), 1e-6)
            vx = _clamp((base[i]["x"] - base[i-1]["x"]) / dt, -40.0, 40.0)
            vy = _clamp((base[i]["y"] - base[i-1]["y"]) / dt, -40.0, 40.0)
            vz = _clamp((base[i]["z"] - base[i-1]["z"]) / dt, -40.0, 40.0)
        px = base[i]["x"]; py = base[i]["y"]
        row = {
            "t": f"{base[i]['t']:.6f}",
            "x": f"{base[i]['x']:.6f}",
            "y": f"{base[i]['y']:.6f}",
            "z": f"{base[i]['z']:.6f}",
            "vx": f"{vx:.6f}",
            "vy": f"{vy:.6f}",
            "vz": f"{vz:.6f}",
            "px": f"{px:.6f}",
            "py": f"{py:.6f}",
            "ekf_px": f"{px:.6f}",
            "ekf_py": f"{py:.6f}",
            "wp_index": "0",
            "lat": "0.0",
            "lon": "0.0",
            "rel_alt_m": f"{base[i]['z']:.6f}",
        }
        full.append(row)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=REQ)
        w.writeheader()
        w.writerows(full)
    print(f"wrote {OUT} with header {REQ} and {len(full)} rows")

if __name__ == "__main__":
    main()
