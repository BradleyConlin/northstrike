#!/usr/bin/env python3
import csv, json, subprocess, sys, pathlib
from datetime import datetime

if len(sys.argv) < 3:
    print("usage: smoke_planner_cost_query.py COST_TIF INPUT.csv [OUT.csv]", file=sys.stderr)
    sys.exit(2)

tif = sys.argv[1]
incsv = sys.argv[2]
outcsv = sys.argv[3] if len(sys.argv) > 3 else "artifacts/maps/probes_out.csv"
pathlib.Path(outcsv).parent.mkdir(parents=True, exist_ok=True)

def probe(lon, lat):
    cmd = ["gdallocationinfo", "-valonly", "-wgs84", tif, str(lon), str(lat)]
    try:
        val = subprocess.check_output(cmd, text=True).strip()
        return float(val) if val not in ("", "nan", "NaN") else None
    except subprocess.CalledProcessError:
        return None

rows_out = []
with open(incsv, newline="") as f:
    for row in csv.DictReader(f):
        lon = float(row["lon"]); lat = float(row["lat"])
        v = probe(lon, lat)
        rows_out.append({"lon": lon, "lat": lat, "cost": v})

with open(outcsv, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["lon","lat","cost"])
    w.writeheader(); w.writerows(rows_out)

summary = {
    "tif": tif,
    "input": incsv,
    "output": outcsv,
    "n": len(rows_out),
    "n_finite": sum(1 for r in rows_out if r["cost"] not in (None,)),
    "ts": datetime.utcnow().isoformat()+"Z",
}
pathlib.Path("artifacts/maps").mkdir(parents=True, exist_ok=True)
with open("artifacts/maps/probes_summary.json", "w") as f:
    json.dump(summary, f, indent=2)
print(json.dumps(summary, indent=2))
