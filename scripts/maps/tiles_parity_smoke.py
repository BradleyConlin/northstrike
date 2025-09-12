#!/usr/bin/env python3
import argparse
import json
import math
import os
import random
import sqlite3
import subprocess
import time


def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"cmd failed: {' '.join(cmd)}\n{r.stderr}")
    return r.stdout.strip()


def mbtiles_bounds(path):
    # MBTiles stores bounds in WGS84 lon,lat,minmax in the metadata table.
    with sqlite3.connect(path) as db:
        row = db.execute("SELECT value FROM metadata WHERE name='bounds'").fetchone()
        if not row or not row[0]:
            raise RuntimeError("MBTiles has no 'bounds' metadata")
        minlon, minlat, maxlon, maxlat = map(float, row[0].split(","))
    return minlon, minlat, maxlon, maxlat


def sample_val(raster, lon, lat, band=1):
    out = sh(["gdallocationinfo", "-valonly", "-wgs84", raster, str(lon), str(lat)])
    vals = [v for v in out.split() if v.strip() != ""]
    if len(vals) == 1:  # single-band Byte/Float32
        v = vals[0]
        if v.lower() == "nan":
            return math.nan
        try:
            return int(round(float(v)))
        except ValueError:
            return math.nan
    # Multi-band (e.g., RGBA MBTiles) — take first band as gray proxy
    try:
        return int(round(float(vals[0])))
    except Exception:
        return math.nan


def scale_float_to_byte(v, max_m=1500.0):
    if math.isnan(v):
        return 0  # NoData → 0 in PNG/MBTiles gray
    v = max(0.0, min(max_m, float(v)))
    # Map [0,max_m] -> [1,255] to avoid full black at 0 unless it's NoData
    dn = 1 + int(round((v / max_m) * 254.0))
    return max(1, min(255, dn))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mbtiles", required=True, help="Gray MBTiles to validate")
    ap.add_argument("--raster", required=True, help="Reference raster (8-bit VRT/GeoTIFF)")
    ap.add_argument(
        "--float32", default=None, help="Optional Float32 cost raster for mapping check"
    )
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--tol", type=int, default=2, help="Allowed DN tolerance for equality checks")
    ap.add_argument("--json-out", default="artifacts/perf/tiles_parity.json")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.json_out), exist_ok=True)

    # Confirm GDAL sees MBTiles (ensures driver present & projection OK)
    # (Driver docs: https://gdal.org/drivers/raster/mbtiles.html)
    minlon, minlat, maxlon, maxlat = mbtiles_bounds(args.mbtiles)

    rng = random.Random(0xC0FFEE)
    ok_equal = 0
    bad_equal = 0
    ok_map = 0
    bad_map = 0
    samples = []
    for _ in range(args.n):
        lon = rng.uniform(minlon, maxlon)
        lat = rng.uniform(minlat, maxlat)

        mb = sample_val(args.mbtiles, lon, lat)
        ref = sample_val(args.raster, lon, lat)

        status_equal = "skip"
        if not math.isnan(mb) and not math.isnan(ref):
            status_equal = "ok" if abs(mb - ref) <= args.tol else "bad"
            ok_equal += status_equal == "ok"
            bad_equal += status_equal == "bad"

        status_map = "skip"
        if args.float32:
            f32 = sample_val(args.float32, lon, lat)
            if math.isnan(f32):
                expected = 0
            else:
                expected = scale_float_to_byte(f32)
            if not math.isnan(mb):
                status_map = "ok" if abs(mb - expected) <= args.tol else "bad"
                ok_map += status_map == "ok"
                bad_map += status_map == "bad"

        samples.append(
            {
                "lon": lon,
                "lat": lat,
                "mb": mb,
                "ref8": ref,
                "map_status": status_map,
                "eq_status": status_equal,
            }
        )

    summary = {
        "mbtiles": args.mbtiles,
        "raster": args.raster,
        "float32": args.float32,
        "n": args.n,
        "tol": args.tol,
        "equal_ok": ok_equal,
        "equal_bad": bad_equal,
        "map_ok": ok_map,
        "map_bad": bad_map,
        "ts": int(time.time()),
    }
    with open(args.json_out, "w") as f:
        json.dump({"summary": summary, "samples": samples}, f, indent=2)

    print(f"EQ (MBTiles vs 8-bit): ok={ok_equal} bad={bad_equal}")
    if args.float32:
        print(f"MAP (MBTiles vs Float32→Byte): ok={ok_map} bad={bad_map}")
    print(f"Wrote {args.json_out}")


if __name__ == "__main__":
    main()
