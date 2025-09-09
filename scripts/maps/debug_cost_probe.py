#!/usr/bin/env python3
# debug_cost_probe.py <AREA>
# Prints nodata, min/max, %valid estimate for maps/costmaps/<AREA>_cost.tif
import sys, os, random, math
from osgeo import gdal, osr

area = sys.argv[1] if len(sys.argv) > 1 else "toronto_downtown"
ras = f"maps/costmaps/{area}_cost.tif"

ds = gdal.Open(ras, gdal.GA_ReadOnly)
if ds is None:
    raise SystemExit(f"ERROR: cannot open {ras}")
band = ds.GetRasterBand(1)
nodata = band.GetNoDataValue()
stats = band.GetStatistics(True, True)  # compute stats
print("Raster:", ras)
print("Size:", ds.RasterXSize, "x", ds.RasterYSize)
print("NoData:", nodata)
print("Stats (min, max, mean, std):", stats)

# quick valid estimate by sampling 2000 random pixels
rng = random.Random(42)
valid = 0
N = min(2000, ds.RasterXSize * ds.RasterYSize)
for _ in range(N):
    px = rng.randrange(ds.RasterXSize)
    py = rng.randrange(ds.RasterYSize)
    v = band.ReadAsArray(px, py, 1, 1)[0, 0]
    if nodata is None:
        if not (math.isnan(v) or math.isinf(v)):
            valid += 1
    else:
        if not (math.isnan(v) or math.isinf(v) or abs(v - nodata) < 1e-12):
            valid += 1
pct = (100.0 * valid / N) if N else 0.0
print(f"Valid-estimate: {valid}/{N} = {pct:.2f}%")
