#!/usr/bin/env python3
# make_inside_points.py <AREA> [N]
# Writes maps/reports/<AREA>_inside_latlon.csv with N random (lat,lon) inside the raster.
import os, sys, random, csv
from osgeo import gdal, osr

area = sys.argv[1] if len(sys.argv) > 1 else "yyz_downtown"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 10
ras = f"maps/costmaps/{area}_cost.tif"

ds = gdal.Open(ras, gdal.GA_ReadOnly)
if ds is None:
    raise SystemExit(f"ERROR: could not open {ras}")
gt = ds.GetGeoTransform()
xsize, ysize = ds.RasterXSize, ds.RasterYSize

src = osr.SpatialReference(); src.ImportFromWkt(ds.GetProjection())
try: src.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
except AttributeError: pass
wgs = osr.SpatialReference(); wgs.ImportFromEPSG(4326)
try: wgs.SetAxisMappingStrategy(osr.OAMS_TRADITIONAL_GIS_ORDER)
except AttributeError: pass
to_wgs = osr.CoordinateTransformation(src, wgs)

rows = [("lat","lon")]
for _ in range(N):
    px = random.randint(0, xsize-1); py = random.randint(0, ysize-1)
    # pixel center
    x = gt[0] + (px + 0.5)*gt[1] + (py + 0.5)*gt[2]
    y = gt[3] + (px + 0.5)*gt[4] + (py + 0.5)*gt[5]
    lon, lat, _ = to_wgs.TransformPoint(x, y)
    rows.append((f"{lat:.12f}", f"{lon:.12f}"))

os.makedirs("maps/reports", exist_ok=True)
out = f"maps/reports/{area}_inside_latlon.csv"
with open(out, "w", newline="") as f:
    csv.writer(f).writerows(rows)
print(f"Wrote {out}")
