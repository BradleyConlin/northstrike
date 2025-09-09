#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   build_cost_from_osm.sh AOI S W N E DEM.tif FILTERED.osm.pbf
# Example:
#   build_cost_from_osm.sh toronto_downtown 43.62 -79.42 43.70 -79.30 \
#     maps/build/toronto_downtown_dtm_wgs84_clip.tif maps/masks/toronto_downtown_filtered.osm.pbf

AOI="${1:?AOI}"
S="${2:?S}"; W="${3:?W}"; N="${4:?N}"; E="${5:?E}"
DEM="${6:?DEM GeoTIFF}"
PBF="${7:?Filtered OSM PBF}"

mkdir -p maps/masks maps/costmaps artifacts/maps/mbtiles .tmp/gdal_osm
export CPL_TMPDIR="$PWD/.tmp/gdal_osm"

BLDG_GPKG="maps/masks/${AOI}_buildings.gpkg"
WATER_GPKG="maps/masks/${AOI}_water.gpkg"
BLDG_MASK="maps/masks/${AOI}_buildings_mask.tif"
WATER_MASK="maps/masks/${AOI}_water_mask.tif"

SLOPE="maps/costmaps/${AOI}_slope_pct.tif"
COST_F32="maps/costmaps/${AOI}_cost_f32.tif"
COST_8BIT="maps/costmaps/${AOI}_cost_8bit.tif"

GRAY_RGBA_TIF="maps/costmaps/${AOI}_cost_gray_rgba.tif"
COLOR_TIF="maps/costmaps/${AOI}_cost_rgba.tif"
GRAY_RGBA_WM="maps/costmaps/${AOI}_cost_gray_rgba_3857.tif"
COLOR_WM="maps/costmaps/${AOI}_cost_rgba_3857.tif"

MBT_GRAY="artifacts/maps/mbtiles/${AOI}_cost_gray.mbtiles"
MBT_COLOR="artifacts/maps/mbtiles/${AOI}_cost_color.mbtiles"

# Byte-domain ramps (0..255). We create them in Step 2.
GRAY_RAMP="scripts/maps/gray_ramp_byte_v1.txt"
COLOR_RAMP="scripts/maps/cost_ramp_byte_v1.txt"

echo "[1/8] Extract buildings → GPKG (from multipolygons: building IS NOT NULL)"
ogr2ogr -overwrite -f GPKG "$BLDG_GPKG" "$PBF" \
  -sql "SELECT * FROM multipolygons WHERE building IS NOT NULL" \
  -dialect SQLite -nln buildings

echo "[2/8] Extract water → GPKG (natural=water OR waterway=riverbank)"
ogr2ogr -overwrite -f GPKG "$WATER_GPKG" "$PBF" \
  -sql "SELECT * FROM multipolygons WHERE \"natural\"='water' OR hstore_get_value(other_tags,'waterway')='riverbank'" \
  -dialect SQLite -nln water

echo "[3/8] Slope (percent) — DEM is geographic; use -s 111120 for meters/degree"
gdaldem slope "$DEM" "$SLOPE" -of GTiff -s 111120 -p

echo "[4/8] Byte masks & burn (NoData=0; strict 0/1)"
for M in "$BLDG_MASK" "$WATER_MASK"; do
  rm -f "$M"
  gdal_create -of GTiff -ot Byte -a_nodata 0 -if "$DEM" -a_nodata 0 -burn 0 \
    -co TILED=YES -co COMPRESS=DEFLATE "$M"
done
gdal_rasterize -burn 1 -at -l buildings "$BLDG_GPKG" "$BLDG_MASK" || echo "No buildings layer pixels burned."
gdal_rasterize -burn 1 -at -l water     "$WATER_GPKG" "$WATER_MASK" || echo "No water layer pixels burned."

echo "[5/8] Cost (Float32) = 1 + 2*slope + 200*buildings + 500*water (NoData=-9999)"
gdal_calc.py --overwrite --type=Float32 --NoDataValue=-9999 \
  -A "$SLOPE" -B "$BLDG_MASK" -C "$WATER_MASK" \
  --outfile="$COST_F32" \
  --calc="1 + 2*A + 200*B + 500*C"

echo "[6/8] 8-bit + alpha prep (scale 0→1500 → 0→255; keep 0 as NoData)"
gdal_translate -of GTiff -ot Byte -a_nodata 0 -scale 0 1500 1 255 \
  "$COST_F32" "$COST_8BIT"

echo "[7/8] Reproject to EPSG:3857 + build MBTiles (gray & color)"
rm -f "$MBT_GRAY" "$MBT_COLOR" "$COLOR_TIF" "$GRAY_RGBA_TIF"

# 1) Colorize 8-bit with alpha using ramps (0=transparent, 'nv' transparent)
gdaldem color-relief -alpha "$COST_8BIT" "$GRAY_RAMP"  "$GRAY_RGBA_TIF"
gdaldem color-relief -alpha "$COST_8BIT" "$COLOR_RAMP" "$COLOR_TIF"

# 2) Reproject overlays to EPSG:3857 and PRESERVE alpha (srcalpha+dstalpha)
GRAY_RGBA_WM="maps/costmaps/${AOI}_cost_gray_rgba_3857.tif"
COLOR_WM="maps/costmaps/${AOI}_cost_rgba_3857.tif"
gdalwarp -t_srs EPSG:3857 -r near -srcalpha -dstalpha -multi -wo NUM_THREADS=ALL_CPUS "$GRAY_RGBA_TIF" "$GRAY_RGBA_WM"
gdalwarp -t_srs EPSG:3857 -r near -srcalpha -dstalpha -multi -wo NUM_THREADS=ALL_CPUS "$COLOR_TIF"      "$COLOR_WM"

# 3) MBTiles from the 3857 RGBA rasters
gdal_translate -of MBTILES -r nearest -co TILE_FORMAT=PNG "$GRAY_RGBA_WM" "$MBT_GRAY"
gdaladdo -r nearest "$MBT_GRAY" 2 4 8 16

gdal_translate -of MBTILES -r nearest -co TILE_FORMAT=PNG "$COLOR_WM" "$MBT_COLOR"
gdaladdo -r nearest "$MBT_COLOR" 2 4 8 16

echo "[8/8] DONE: $AOI → $MBT_GRAY ; $MBT_COLOR"
