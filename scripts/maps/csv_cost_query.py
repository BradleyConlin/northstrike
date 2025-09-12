#!/usr/bin/env python3
import csv
import subprocess
import sys

# Usage: python scripts/maps/csv_cost_query.py AREA input.csv [out.csv]
if len(sys.argv) < 3:
    print("Usage: csv_cost_query.py AREA input.csv [out.csv]", file=sys.stderr)
    sys.exit(1)

AREA, input_csv = sys.argv[1], sys.argv[2]
out_csv = sys.argv[3] if len(sys.argv) >= 4 else f"maps/reports/{AREA}_cost_query.csv"
raster = f"maps/costmaps/{AREA}_cost.tif"


def run(cmd, **kw):
    return subprocess.run(cmd, check=False, capture_output=True, text=True, **kw)


def get_epsg(path):
    p = run(["gdalsrsinfo", "-o", "epsg", path])
    if p.stdout:
        for tok in p.stdout.split():
            if tok.startswith("EPSG:"):
                return tok.split(":")[1]
    p = run(["gdalinfo", path])
    if p.stdout:
        for tok in p.stdout.split():
            if tok.startswith("EPSG:"):
                return tok.split(":")[1]
    return "32617"


def to4326(epsg, x, y):
    p = subprocess.run(
        ["gdaltransform", "-s_srs", f"EPSG:{epsg}", "-t_srs", "EPSG:4326"],
        input=f"{x} {y}\n",
        capture_output=True,
        text=True,
        check=False,
    )
    vals = p.stdout.strip().split()
    return (float(vals[1]), float(vals[0])) if len(vals) >= 2 else (None, None)  # lat, lon


def get_extent_wgs84(path):
    gi = run(["gdalinfo", path]).stdout
    import re

    def grab(label):
        m = re.search(rf"{label}\s*\(\s*([-\d\.]+),\s*([-\d\.]+)\s*\)", gi)
        return (float(m.group(1)), float(m.group(2))) if m else (None, None)

    ulx, uly = grab("Upper Left")
    lrx, lry = grab("Lower Right")
    epsg = get_epsg(path)
    ul_lat, ul_lon = to4326(epsg, ulx, uly)
    lr_lat, lr_lon = to4326(epsg, lrx, lry)
    min_lon, max_lon = sorted([ul_lon, lr_lon])
    min_lat, max_lat = sorted([lr_lat, ul_lat])
    return (min_lon, min_lat, max_lon, max_lat), epsg


def inside_extent(lon, lat, extent):
    mnx, mny, mxx, mxy = extent
    return (mnx <= lon <= mxx) and (mny <= lat <= mxy)


def sample_cost(lon, lat):
    p = run(["gdallocationinfo", "-wgs84", "-valonly", raster, str(lon), str(lat)])
    v = (p.stdout or "").strip()
    if (not v) or v == "-9999":
        return "NaN"
    try:
        float(v)
        return v
    except Exception:
        return "NaN"


extent, epsg = get_extent_wgs84(raster)

with open(input_csv, newline="") as f, open(out_csv, "w", newline="") as g:
    r = csv.reader(f)
    w = csv.writer(g)
    headers = next(r)
    idx = {h.lower(): i for i, h in enumerate(headers)}
    lat_idx = next((i for k, i in idx.items() if k in ("lat", "latitude")), None)
    lon_idx = next((i for k, i in idx.items() if k in ("lon", "lng", "longitude")), None)
    x_idx = next((i for k, i in idx.items() if k in ("x", "easting", "utm_e", "utm_easting")), None)
    y_idx = next(
        (i for k, i in idx.items() if k in ("y", "northing", "utm_n", "utm_northing")), None
    )
    w.writerow(["lat", "lon", "cost"])

    for row in r:
        lat = lon = None
        # Prefer explicit lat/lon if valid & inside raster extent
        if lat_idx is not None and lon_idx is not None:
            try:
                lat = float(row[lat_idx])
                lon = float(row[lon_idx])
                if not (
                    -90 <= lat <= 90 and -180 <= lon <= 180 and inside_extent(lon, lat, extent)
                ):
                    lat = lon = None
            except Exception:
                lat = lon = None
        # Else fall back to projected X/Y -> lon/lat
        if (lat is None or lon is None) and x_idx is not None and y_idx is not None:
            try:
                x = float(row[x_idx])
                y = float(row[y_idx])
                lat, lon = to4326(epsg, x, y)
            except Exception:
                lat = lon = None
        if lat is None or lon is None:
            w.writerow(["NaN", "NaN", "NaN"])
        else:
            w.writerow([f"{lat}", f"{lon}", sample_cost(lon, lat)])

print(f"Wrote {out_csv}")
