#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   maps_v2/bin/build_aoi.sh yyz_downtown 43.6283082 -79.4218346 43.7015733 -79.3081948
# Args: AREA  S            W           N            E   (lat/lon degrees)
AREA="${1:?area}"; S="${2:?S}"; W="${3:?W}"; N="${4:?N}"; E="${5:?E}"

# ---- Paths -------------------------------------------------------------------
ROOT="${ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
V2="$ROOT/maps_v2"
BUILD="$V2/build/$AREA"
MBTILES="$V2/mbtiles/${AREA}_cost_color.mbtiles"
RAMP="${RAMP:-$V2/ramps/cost_ramp_default.txt}"

mkdir -p "$BUILD" "$V2/mbtiles"

# ---- DEM source ---------------------------------------------------------------
# If you already have a HRDEM DTM in lat/lon (EPSG:4326), put it here to reuse:
SRC_DEM_LONLAT_DEFAULT="$ROOT/maps/build/${AREA}_dtm1m.tif"
SRC_DEM_LONLAT="${SRC_DEM_LONLAT:-$SRC_DEM_LONLAT_DEFAULT}"

if [ ! -f "$SRC_DEM_LONLAT" ]; then
  echo "[!] Missing DEM at $SRC_DEM_LONLAT"
  echo "    Place an HRDEM 1 m DTM (lat/lon) here or set SRC_DEM_LONLAT=... and re-run."
  echo "    HRDEM Mosaic provides 1 m/2 m via WCS/STAC; see product docs."
  exit 2
fi

# ---- Compute UTM EPSG from AOI center lon ------------------------------------
CENTER_LON=$(python3 - <<PY
print((float("$W")+float("$E"))/2.0)
PY
)
ZONE=$(python3 - <<PY
lon=float("$CENTER_LON"); print(int((lon+180)//6)+1)
PY
)
EPSG=$((32600 + ZONE))   # WGS84 / UTM zone XXN
echo "[i] Using UTM EPSG:$EPSG for lon=$CENTER_LON (zone=$ZONE)"

# ---- Reproject & clip to UTM 1 m grid ---------------------------------------
UTM_DEM="$BUILD/${AREA}_dtm1m_utm.tif"
echo "[1/6] DEM → UTM $EPSG @ 1 m (clip to bbox)"
gdalwarp -t_srs "EPSG:$EPSG" -te_srs EPSG:4326 -te "$W" "$S" "$E" "$N" \
  -tr 1 1 -tap -r bilinear -of COG \
  -co COMPRESS=DEFLATE -co PREDICTOR=2 -co BIGTIFF=IF_NEEDED \
  "$SRC_DEM_LONLAT" "$UTM_DEM"

# ---- Slope in percent (metric DEM => no scale needed) ------------------------
SLOPE="$BUILD/${AREA}_slope_pct.tif"
echo "[2/6] Slope (%) from metric DEM"
gdaldem slope "$UTM_DEM" "$SLOPE" -p -compute_edges  # -p = percent
# (If DEM were in degrees, we'd use -s 111120; here DEM is meters.)

# ---- OSM Buildings fetch → GPKG, then burn mask ------------------------------
B_GPKG="$BUILD/${AREA}_buildings.gpkg"
if [ ! -f "$B_GPKG" ]; then
  echo "[3/6] Fetch OSM buildings via Overpass (polite UA)"
  TMP_OSM="$BUILD/${AREA}_buildings.osm"
  curl -sS -A "northstrike-maps/1.0 (contact: ops@northstrike.local)" \
    -G "https://overpass-api.de/api/interpreter" \
    --data-urlencode "data=[out:xml];(way['building']($S,$W,$N,$E);rel['building']($S,$W,$N,$E););(._;>;);out body;" \
    -o "$TMP_OSM" || true
  if [ ! -s "$TMP_OSM" ]; then
    curl -sS -A "northstrike-maps/1.0 (contact: ops@northstrike.local)" \
      -G "https://overpass.kumi.systems/api/interpreter" \
      --data-urlencode "data=[out:xml];(way['building']($S,$W,$N,$E);rel['building']($S,$W,$N,$E););(._;>;);out body;" \
      -o "$TMP_OSM"
  fi
  ogr2ogr -f GPKG "$B_GPKG" "$TMP_OSM" multipolygons -oo USE_CUSTOM_INDEXING=NO
fi

echo "[4/6] Burn buildings → 0/1 raster aligned to DEM"
B_MASK="$BUILD/${AREA}_buildings_mask.tif"
gdal_calc.py -A "$UTM_DEM" --calc="A*0" --type=Byte --NoDataValue=0 --overwrite --outfile "$B_MASK"
gdal_rasterize -burn 1 -at -l multipolygons "$B_GPKG" "$B_MASK"

# ---- Float32 planner truth cost ----------------------------------------------
COST_F32="$BUILD/${AREA}_cost_f32.tif"
echo "[5/6] Compose Float32 cost (2*slope + 200*buildings)"
gdal_calc.py -A "$SLOPE" -B "$B_MASK" --type=Float32 --NoDataValue=-9999 --overwrite \
  --calc="2*A + 200*B" --outfile "$COST_F32"

# ---- Publish MBTiles (RGBA ramp + 3857 + overviews) --------------------------
echo "[6/6] Publish MBTiles (RGBA) for visualization"
BYTE_0400="$BUILD/${AREA}_cost_0_400_byte.tif"
COLOR_UTM="$BUILD/${AREA}_cost_color_utm.tif"
COLOR_3857="$BUILD/${AREA}_cost_color_3857.tif"

gdal_translate -of GTiff -ot Byte -a_nodata 0 -scale 0 400 0 400 "$COST_F32" "$BYTE_0400"
gdaldem color-relief -alpha "$BYTE_0400" "$RAMP" "$COLOR_UTM"
gdalwarp -t_srs EPSG:3857 -r near -of GTiff -co TILED=YES -co COMPRESS=DEFLATE -co PREDICTOR=2 \
  "$COLOR_UTM" "$COLOR_3857"
rm -f "$MBTILES"
gdal_translate -of MBTILES "$COLOR_3857" "$MBTILES"
gdaladdo -r nearest "$MBTILES" 2 4 8 16

echo
echo "DONE. Outputs:"
echo "  Float32 cost: $COST_F32   (planner truth)"
echo "  MBTiles:      $MBTILES    (visualization)"
