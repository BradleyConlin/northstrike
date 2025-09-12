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


def _sample_float(path, lon, lat, extra=None, band=None):
    """Return a single float value (or NaN) from gdallocationinfo."""
    cmd = ["gdallocationinfo", "-valonly", "-wgs84"]
    if extra:
        cmd += list(extra)
    if band is not None:
        cmd += ["-b", str(band)]
    cmd += [path, str(lon), str(lat)]
    out = sh(cmd).strip()
    # When no -b is given and dataset has multiple bands, gdallocationinfo prints e.g. "R G B [A]".
    parts = [p for p in out.split() if p.strip() != ""]
    if len(parts) >= 1:
        try:
            return float(parts[0])  # first channel if multiple
        except ValueError:
            return math.nan
    return math.nan


def sample_val_int(path, lon, lat, extra=None, band=None, luma=False):
    """Return integer DN. If luma=True, compute from RGB bands 1..3."""
    if luma:
        r = _sample_float(path, lon, lat, extra=extra, band=1)
        g = _sample_float(path, lon, lat, extra=extra, band=2)
        b = _sample_float(path, lon, lat, extra=extra, band=3)
        if any(math.isnan(v) for v in (r, g, b)):
            return 0
        v = 0.2126 * r + 0.7152 * g + 0.0722 * b
    else:
        v = _sample_float(path, lon, lat, extra=extra, band=band)
    if math.isnan(v):
        return 0
    try:
        return int(round(v))
    except Exception:
        return 0


def scale_float_to_byte(v, max_m=1500.0):
    if math.isnan(v):
        return 0  # NoData → 0 in PNG/MBTiles gray
    v = max(0.0, min(max_m, float(v)))
    # Map [0,max_m] -> [1,255] to avoid full black at 0 unless it's NoData
    dn = 1 + int(round((v / max_m) * 254.0))
    return max(1, min(255, dn))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mbtiles", required=True, help="Target MBTiles (gray or color)")
    ap.add_argument("--raster", required=True, help="Reference raster (8-bit VRT/GeoTIFF or RGBA)")
    ap.add_argument(
        "--float32", default=None, help="Optional Float32 cost raster for mapping check"
    )
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--tol", type=int, default=2, help="Allowed DN tolerance for equality checks")
    ap.add_argument("--json-out", default="artifacts/perf/tiles_parity.json")
    # MBTiles reading controls
    ap.add_argument(
        "--zoom", type=int, default=None, help="Force MBTiles ZOOM_LEVEL via GDAL open option"
    )
    ap.add_argument(
        "--ovr", type=int, default=None, help="Force overview index for gdallocationinfo"
    )
    # Band/luma controls
    ap.add_argument(
        "--mb-band", type=int, default=None, help="MBTiles band to read (1=R/Gray, 2=G, 3=B, 4=A)"
    )
    ap.add_argument("--ref-band", type=int, default=None, help="Reference raster band to read")
    ap.add_argument(
        "--mb-luma", action="store_true", help="Compute luminance from MBTiles RGB (bands 1..3)"
    )
    args = ap.parse_args()

    os.makedirs(os.path.dirname(args.json_out), exist_ok=True)

    # Confirm GDAL sees MBTiles (ensures driver present & projection OK)
    minlon, minlat, maxlon, maxlat = mbtiles_bounds(args.mbtiles)

    # Build extra flags for MBTiles access if requested
    mbtiles_extra = []
    if args.zoom is not None:
        mbtiles_extra += ["-oo", f"ZOOM_LEVEL={args.zoom}"]
    if args.ovr is not None:
        mbtiles_extra += ["-overview", str(args.ovr)]

    rng = random.Random(0xC0FFEE)
    ok_equal = bad_equal = ok_map = bad_map = 0
    samples = []

    for _ in range(args.n):
        lon = rng.uniform(minlon, maxlon)
        lat = rng.uniform(minlat, maxlat)

        mb = sample_val_int(
            args.mbtiles, lon, lat, extra=mbtiles_extra, band=args.mb_band, luma=args.mb_luma
        )
        ref = sample_val_int(args.raster, lon, lat, band=args.ref_band)

        status_equal = "skip"
        if mb is not None and ref is not None:
            status_equal = "ok" if abs(mb - ref) <= args.tol else "bad"
            ok_equal += 1 if status_equal == "ok" else 0
            bad_equal += 1 if status_equal == "bad" else 0

        status_map = "skip"
        if args.float32:
            f32 = _sample_float(args.float32, lon, lat)
            expected = 0 if math.isnan(f32) else scale_float_to_byte(f32)
            status_map = "ok" if abs(mb - expected) <= args.tol else "bad"
            ok_map += 1 if status_map == "ok" else 0
            bad_map += 1 if status_map == "bad" else 0

        samples.append(
            {
                "lon": lon,
                "lat": lat,
                "mb": mb,
                "ref": ref,
                "eq_status": status_equal,
                "map_status": status_map,
            }
        )

    summary = {
        "mbtiles": args.mbtiles,
        "raster": args.raster,
        "float32": args.float32,
        "n": args.n,
        "tol": args.tol,
        "zoom": args.zoom,
        "ovr": args.ovr,
        "mb_band": args.mb_band,
        "ref_band": args.ref_band,
        "mb_luma": args.mb_luma,
        "equal_ok": ok_equal,
        "equal_bad": bad_equal,
        "map_ok": ok_map,
        "map_bad": bad_map,
        "ts": int(time.time()),
    }
    with open(args.json_out, "w") as f:
        json.dump({"summary": summary, "samples": samples}, f, indent=2)

    print(f"EQ (MBTiles vs ref): ok={ok_equal} bad={bad_equal}")
    if args.float32:
        print(f"MAP (MBTiles vs Float32→Byte): ok={ok_map} bad={bad_map}")
    print(f"Wrote {args.json_out}")


if __name__ == "__main__":
    main()
