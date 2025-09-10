#!/usr/bin/env python3
import os, sys
import numpy as np
from osgeo import gdal, osr

area = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("AREA", "toronto_downtown")
dst = f"maps/build/{area}_dtm1m.tif"
os.makedirs(os.path.dirname(dst), exist_ok=True)

if os.path.exists(dst):
    print(f"[smoke-dem] exists: {dst}")
    raise SystemExit(0)

w = h = 256
arr = (np.arange(h, dtype=np.float32)[:,None] + np.arange(w, dtype=np.float32)[None,:])

origin_lon, origin_lat = -79.395, 43.653  # near Toronto City Hall
px, py = 1e-5, -1e-5                      # ~1.1 m/px in degrees; negative y size
gt = (origin_lon, px, 0.0, origin_lat, 0.0, py)

drv = gdal.GetDriverByName("GTiff")
ds = drv.Create(dst, w, h, 1, gdal.GDT_Float32, options=["COMPRESS=LZW","TILED=YES"])
ds.SetGeoTransform(gt)
srs = osr.SpatialReference(); srs.ImportFromEPSG(4326)
ds.SetProjection(srs.ExportToWkt())
band = ds.GetRasterBand(1)
band.SetNoDataValue(-9999)
band.WriteArray(arr)
band.FlushCache(); ds.FlushCache(); ds = None
print(f"[smoke-dem] created {dst}")
