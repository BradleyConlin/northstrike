#!/usr/bin/env python3
import cgi, json, subprocess, sys, os

print("Content-Type: application/json")
print("Access-Control-Allow-Origin: *")
print()

fs = cgi.FieldStorage()
area = fs.getfirst("area", "aoi_rural_mo")
lat  = fs.getfirst("lat")
lon  = fs.getfirst("lon")

def bail(msg):
    print(json.dumps({"ok": False, "error": msg}))
    sys.exit(0)

if lat is None or lon is None:
    bail("missing lat/lon")

raster = os.path.join("maps", "costmaps", f"{area}_cost.tif")
if not os.path.exists(raster):
    bail(f"missing raster: {raster}")

# Use GDAL to sample the raster at lon/lat (WGS84)
cmd = ["gdallocationinfo", "-wgs84", "-valonly", raster, lon, lat]
try:
    out = subprocess.check_output(cmd, stderr=subprocess.STDOUT, text=True).strip()
    val = None if out == "" else float(out)
    # Treat NoData as null
    if val == -9999:
        val = None
    print(json.dumps({"ok": True, "area": area, "lat": float(lat), "lon": float(lon), "cost": val}))
except subprocess.CalledProcessError as e:
    bail(f"gdallocationinfo failed: {e.output}")
