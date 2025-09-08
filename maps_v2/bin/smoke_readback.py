#!/usr/bin/env python3
import csv, json, math, subprocess, sys, pathlib, statistics as stats
root = subprocess.check_output(["git","rev-parse","--show-toplevel"]).decode().strip()
area = sys.argv[1] if len(sys.argv)>1 else "yyz_downtown"
pts_csv = sys.argv[2] if len(sys.argv)>2 else "/tmp/yyz_pts.csv"
cost = pathlib.Path(root)/"maps_v2"/"build"/area/(f"{area}_cost_f32.tif")
out_dir = pathlib.Path(root)/"maps_v2"/"build"/area
out_dir.mkdir(parents=True, exist_ok=True)
out_csv = out_dir/(f"{area}_readback.csv")
out_json = out_dir/(f"{area}_readback_summary.json")

vals = []
with open(pts_csv) as f, open(out_csv, "w", newline="") as g:
    r = csv.DictReader(f)
    w = csv.writer(g); w.writerow(["name","lat","lon","value"])
    for row in r:
        if row["name"]=="name": continue
        lon, lat = row["lon"], row["lat"]
        v = subprocess.run(
            ["gdallocationinfo","-wgs84","-valonly",str(cost),lon,lat],
            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
        ).stdout.strip()
        try:
            x = float(v);
            if x != -9999 and not math.isnan(x): vals.append(x)
        except: pass
        w.writerow([row["name"], lat, lon, v or "NaN"])

summary = {
    "n_finite": len(vals),
    "min": min(vals) if vals else None,
    "max": max(vals) if vals else None,
    "mean": stats.fmean(vals) if vals else None,
}
out_json.write_text(json.dumps(summary, indent=2))
print(f"Wrote {out_csv} and {out_json}")
