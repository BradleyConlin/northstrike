#!/usr/bin/env python3
"""
csv_cost_query_cli.py
Query Float32 cost raster at (lat, lon) points and write a CSV with costs.

Usage:
  python scripts/maps/csv_cost_query_cli.py <AREA> <input.csv> [output.csv]

Input CSV must have headers containing lat/lon (accepted: lat|latitude, lon|lng|long|longitude).
Output written to maps/reports/<AREA>_cost_query.csv with columns: lat,lon,cost

Notes:
- Uses GDAL Python API end-to-end (no subprocess).
- Robust to GDAL variants: InvGeoTransform() may return (ok, inv) or just inv.
- Uses traditional GIS axis order when available.
"""
from __future__ import annotations

import csv
import math
import os
import sys

try:
    from osgeo import gdal, osr
except Exception:
    print(
        "ERROR: GDAL unavailable. Pin numpy<2 and install python3-gdal.",
        file=sys.stderr,
    )
    raise


def inv_gt_compat(gt):
    """Return inverse geotransform 6-tuple regardless of GDAL signature."""
    res = gdal.InvGeoTransform(gt)
    if isinstance(res, list | tuple):
        if len(res) == 6:
            return res
        if len(res) == 2:
            ok, inv_gt = res
            if not ok:
                raise RuntimeError("InvGeoTransform failed")
            return inv_gt
    return res  # hope it's already the 6-tuple


def open_raster(path: str):
    ds = gdal.Open(path, gdal.GA_ReadOnly)
    if ds is None:
        raise RuntimeError(f"Could not open raster: {path}")
    band = ds.GetRasterBand(1)
    nodata = band.GetNoDataValue()
    inv_gt = inv_gt_compat(ds.GetGeoTransform())

    src_srs = osr.SpatialReference()
    src_srs.ImportFromWkt(ds.GetProjection())
    try:
        src_srs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    except AttributeError:
        pass

    wgs84 = osr.SpatialReference()
    wgs84.ImportFromEPSG(4326)
    try:
        wgs84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
    except AttributeError:
        pass

    to_src = osr.CoordinateTransformation(wgs84, src_srs)
    return ds, band, nodata, inv_gt, to_src


def latlon_to_pixel(lat: float, lon: float, to_src, inv_gt) -> tuple[int, int] | None:
    # Transform WGS84 (lon,lat) -> raster CRS (x,y). Guard failures.
    try:
        x, y, _ = to_src.TransformPoint(lon, lat)
    except Exception:
        return None
    if math.isnan(x) or math.isnan(y) or math.isinf(x) or math.isinf(y):
        return None
    px_f, py_f = gdal.ApplyGeoTransform(inv_gt, x, y)
    if math.isnan(px_f) or math.isnan(py_f) or math.isinf(px_f) or math.isinf(py_f):
        return None
    return int(round(px_f)), int(round(py_f))


def sample_pixel(ds, band, px: int, py: int):
    if px < 0 or py < 0 or px >= ds.RasterXSize or py >= ds.RasterYSize:
        return None
    arr = band.ReadAsArray(px, py, 1, 1)
    if arr is None:
        return None
    return float(arr[0, 0])


def find_lat_lon_columns(header):
    lat_idx = lon_idx = -1
    for i, name in enumerate(header):
        n = (name or "").strip().lower()
        if n in ("lat", "latitude"):
            lat_idx = i
        if n in ("lon", "lng", "long", "longitude"):
            lon_idx = i
    if lat_idx == -1 or lon_idx == -1:
        raise RuntimeError(f"Could not find lat/lon columns in header: {header}")
    return lat_idx, lon_idx


def main():
    if len(sys.argv) < 3:
        print("Usage: csv_cost_query_cli.py <AREA> <input.csv> [output.csv]", file=sys.stderr)
        sys.exit(2)

    area = sys.argv[1]
    in_csv = sys.argv[2]
    out_csv = sys.argv[3] if len(sys.argv) > 3 else f"maps/reports/{area}_cost_query.csv"
    raster = f"maps/costmaps/{area}_cost.tif"

    ds, band, nodata, inv_gt, to_src = open_raster(raster)
    os.makedirs(os.path.dirname(out_csv), exist_ok=True)

    rows_out = [["lat", "lon", "cost"]]
    with open(in_csv, newline="") as f:
        rdr = csv.reader(f)
        header = next(rdr)
        lat_idx, lon_idx = find_lat_lon_columns(header)

        for row in rdr:
            if not row or len(row) <= max(lat_idx, lon_idx):
                continue
            try:
                lat = float(str(row[lat_idx]).strip())
                lon = float(str(row[lon_idx]).strip())
            except ValueError:
                rows_out.append(["NaN", "NaN", "NaN"])
                continue

            pix = latlon_to_pixel(lat, lon, to_src, inv_gt)
            if pix is None:
                rows_out.append([f"{lat:.12f}", f"{lon:.12f}", "NaN"])
                continue

            px, py = pix
            val = sample_pixel(ds, band, px, py)

            if val is None or (
                nodata is not None and (math.isnan(val) or abs(val - nodata) < 1e-12)
            ):
                cost_str = "NaN"
            else:
                cost_str = f"{val:.6f}"

            rows_out.append([f"{lat:.12f}", f"{lon:.12f}", cost_str])

    with open(out_csv, "w", newline="") as f:
        csv.writer(f).writerows(rows_out)

    print(f"Wrote {out_csv}")


if __name__ == "__main__":
    main()
