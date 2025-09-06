#!/usr/bin/env python3
"""
Query Float32 cost at (lat,lon) from a CSV using GDAL only (no subprocess).
Input CSV must have headers 'lat' and 'lon' (case-insensitive). Output goes to
maps/reports/<AREA>_cost_query.csv with columns lat,lon,cost.
"""
import csv, os, sys, math
from typing import Tuple
from osgeo import gdal, osr

def inv_gt_compat(gt):
    """Return (ok, inv_gt) regardless of GDAL Python signature."""
    res = gdal.InvGeoTransform(gt)
    # Newer builds sometimes return just the 6-tuple
    if isinstance(res, (list, tuple)) and len(res) == 6:
        return True, res
    # Classic signature: (ok, inv_gt)
    if isinstance(res, (list, tuple)) and len(res) == 2:
        ok, inv_gt = res
        return bool(ok), inv_gt
    # Fallback
    return True, res

def open_raster(raster_path):
    ds = gdal.Open(raster_path, gdal.GA_ReadOnly)
    if ds is None:
        sys.exit(f"ERROR: cannot open raster: {raster_path}")
    band = ds.GetRasterBand(1)
    nodata = band.GetNoDataValue()
    gt = ds.GetGeoTransform()
    ok, inv_gt = inv_gt_compat(gt)
    if not ok:
        sys.exit("ERROR: InvGeoTransform failed")
    proj_wkt = ds.GetProjection()
    return ds, band, nodata, gt, inv_gt, proj_wkt

def build_transform_to_raster(proj_wkt):
    """WGS84 (lon,lat) -> raster CRS transform."""
    wgs84 = osr.SpatialReference()
    wgs84.ImportFromEPSG(4326)
    # Keep traditional GIS axis order (lon,lat)
    wgs84.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

    ras = osr.SpatialReference()
    if proj_wkt:
        ras.ImportFromWkt(proj_wkt)
    else:
        ras.ImportFromEPSG(4326)
    ras.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)

    return osr.CoordinateTransformation(wgs84, ras)

def sample_pixel(band, px: int, py: int):
    """Read a single pixel (nearest)."""
    return band.ReadAsArray(px, py, 1, 1)[0, 0]

def main():
    if len(sys.argv) != 3:
        print("Usage: csv_cost_query_gdal.py <AREA> <input.csv>", file=sys.stderr)
        sys.exit(2)

    area = sys.argv[1]
    in_csv = sys.argv[2]
    raster = f"maps/costmaps/{area}_cost.tif"
    out_csv = f"maps/reports/{area}_cost_query.csv"
    os.makedirs("maps/reports", exist_ok=True)

    ds, band, NODATA, GT, INV_GT, PROJ_WKT = open_raster(raster)
    XSIZE, YSIZE = ds.RasterXSize, ds.RasterYSize
    to_raster = build_transform_to_raster(PROJ_WKT)

    def world_to_pixel(x, y) -> Tuple[int, int]:
        px_f, py_f = gdal.ApplyGeoTransform(INV_GT, x, y)
        # nearest neighbor indices
        return int(round(px_f)), int(round(py_f))

    rows_out = []
    with open(in_csv, newline="") as f:
        r = csv.DictReader(f)
        # normalize headers
        hdrs = {k.lower(): k for k in r.fieldnames or []}
        if not (("lat" in hdrs) and ("lon" in hdrs)):
            sys.exit("ERROR: input CSV must have headers 'lat' and 'lon'")
        for rec in r:
            try:
                lat = float(rec[hdrs["lat"]])
                lon = float(rec[hdrs["lon"]])
            except Exception:
                rows_out.append({"lat": "NaN", "lon": "NaN", "cost": "NaN"})
                continue
            # transform to raster CRS
            x, y, *_ = to_raster.TransformPoint(lon, lat)
            px, py = world_to_pixel(x, y)
            if px < 0 or py < 0 or px >= XSIZE or py >= YSIZE:
                rows_out.append({"lat": lat, "lon": lon, "cost": "NaN"})
                continue
            val = float(sample_pixel(band, px, py))
            if NODATA is not None and math.isclose(val, NODATA):
                rows_out.append({"lat": lat, "lon": lon, "cost": "NaN"})
            else:
                rows_out.append({"lat": lat, "lon": lon, "cost": f"{val:.6g}"})

    with open(out_csv, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["lat", "lon", "cost"])
        w.writeheader()
        w.writerows(rows_out)
    print(f"Wrote {out_csv}")

if __name__ == "__main__":
    main()
