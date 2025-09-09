#!/usr/bin/env bash
set -euo pipefail

# Usage: scripts/maps/publish_mbtiles_from_cost.sh toronto_downtown
AREA="${1:-toronto_downtown}"

REPO="${REPO:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
cd "$REPO"

# Inputs / outputs
COST_F32="maps/costmaps/${AREA}_cost.tif"               # Float32, NoData=-9999 (planner truth)
RAMP="scripts/maps/cost_ramp_${AREA}.txt"               # color-relief ramp in 0..400 domain
STYLE_MAX=400                                           # fixed, visible domain for styling
BYTE_0400="maps/costmaps/${AREA}_cost_0_400_byte.tif"   # 0..400 Byte for colorizing
COLOR_UTM="maps/costmaps/${AREA}_cost_color_utm.tif"    # RGBA in source CRS
COLOR_3857="maps/costmaps/${AREA}_cost_color_3857.tif"  # RGBA in EPSG:3857
MBTILES="artifacts/maps/mbtiles/${AREA}_cost_color.mbtiles"

# Checks
test -f "$COST_F32" || { echo "ERROR: missing $COST_F32"; exit 2; }
test -f "$RAMP"     || { echo "ERROR: missing $RAMP"; exit 2; }
mkdir -p "$(dirname "$MBTILES")"

echo "[1/5] Clamp & scale Float32 → Byte 0..400 (0 keeps transparency later)"
gdal_translate -of GTiff -ot Byte -a_nodata 0 \
  -scale 0 ${STYLE_MAX} 0 ${STYLE_MAX} \
  "$COST_F32" "$BYTE_0400"

echo "[2/5] Apply color ramp (RGBA, alpha from ramp 'nv' + '0' rule)"
gdaldem color-relief -alpha "$BYTE_0400" "$RAMP" "$COLOR_UTM"

echo "[3/5] Reproject to Web Mercator (EPSG:3857) for XYZ/MBTiles"
gdalwarp -t_srs EPSG:3857 -r near -of GTiff \
  -co TILED=YES -co COMPRESS=DEFLATE -co PREDICTOR=2 \
  "$COLOR_UTM" "$COLOR_3857"

echo "[4/5] Create MBTiles (XYZ scheme) and build overviews"
rm -f "$MBTILES"
gdal_translate -of MBTILES "$COLOR_3857" "$MBTILES"
gdaladdo -r nearest "$MBTILES" 2 4 8 16

echo "[5/5] Summarize"
gdalinfo "$MBTILES" | sed -n '1,80p'
echo "OK: $MBTILES"
echo
echo "To serve locally:"
echo "  docker run --rm -p 8001:8000 -v \"$(pwd)/artifacts/maps/mbtiles:/tilesets\" ghcr.io/consbio/mbtileserver:latest"
echo "Then open: http://127.0.0.1:8001/services/${AREA}_cost_color/map"
