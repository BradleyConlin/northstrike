#!/usr/bin/env bash
set -euo pipefail
# Inputs:
#   AREA=<name>  (required)
#   DEM=<path/to/dem.tif> (optional; if absent, you must fetch one first)
# Requires: gdal_calc.py, gdal_rasterize, gdaldem, gdal_edit.py, gdal_translate

: "${AREA:?Set AREA=<name>}"
BUILD="maps/build"
COSTS="maps/costmaps"
SRC="maps/src"
mkdir -p "$BUILD" "$COSTS" "$SRC"

DEM_PATH="${DEM:-$BUILD/${AREA}_dtm1m.tif}"
MSK="$BUILD/${AREA}_buildings_mask.tif"
SLOPE="$BUILD/${AREA}_slope.tif"
COST="$COSTS/${AREA}_cost.tif"
GJ="$SRC/${AREA}_buildings.geojson"

if [ ! -f "$DEM_PATH" ]; then
  echo "Missing DEM at $DEM_PATH. Fetch one first." >&2
  exit 2
fi

# 1) Slope (%)
gdaldem slope -p "$DEM_PATH" "$SLOPE" -compute_edges

# 2) Mask scaffold: explicit zero image (Byte, no NoData)
gdal_calc.py --overwrite --calc="0" --type=Byte --outfile "$MSK" -A "$DEM_PATH"

# 2b) Burn buildings=1 if we have GeoJSON, then clamp to 0/1 and remove NoData
if [ -f "$GJ" ]; then
  gdal_rasterize -burn 1 -at "$GJ" "$MSK"
  # Force binary 0/1 (some builds can leave 255s); then drop any NoData flag
  gdal_calc.py --overwrite -A "$MSK" --calc="(A>0)" --type=Byte --outfile "${MSK}.tmp.tif"
  mv "${MSK}.tmp.tif" "$MSK"
  gdal_edit.py -unsetnodata "$MSK"
  rm -f "${MSK}.aux.xml" || true
else
  echo "[warn] No buildings GeoJSON at $GJ; leaving mask at zeros."
fi

# 3) Cost combine (Float32; tune weights per mission)
gdal_calc.py --overwrite -A "$SLOPE" -B "$MSK" --type=Float32 \
  --NoDataValue=-9999 --calc="(A*2.0)+(B*200.0)" --outfile "$COST"

# 4) Previews (8-bit with explicit scaling to avoid blank PNGs)
gdal_translate -of PNG -ot Byte -a_nodata 0 -scale 0 15 1 255 "$SLOPE" "${SLOPE%.tif}.png" >/dev/null
gdal_translate -of PNG -ot Byte               -scale 0  1 0 255 "$MSK"   "${MSK%.tif}.png"   >/dev/null
gdal_translate -of PNG -ot Byte -a_nodata 0 -scale 0 500 1 255 "$COST"  "${COST%.tif}.png"  >/dev/null

echo "[ok] Built:"
ls -lh "$SLOPE" "${SLOPE%.tif}.png" "$MSK" "${MSK%.tif}.png" "$COST" "${COST%.tif}.png"
