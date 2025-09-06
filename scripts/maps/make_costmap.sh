#!/usr/bin/env bash
set -euo pipefail

# Build a costmap for AREA using a YAML weights file.
# Inputs (expected if previously fetched/built):
#   maps/build/<AREA>_dtm1m.tif            # 1 m DTM (UTM)
#   maps/src/<AREA>_osm.osm                # OSM XML (optional but recommended)
#   maps/build/<AREA>_buildings_mask.tif   # may already exist; we will create/overwrite
# Outputs:
#   maps/build/<AREA>_slope.tif(.png)
#   maps/build/<AREA>_{buildings,roads,water,parks}_mask.tif
#   maps/costmaps/<AREA>_cost.tif          # Float32 COG (planner source)
#   maps/costmaps/<AREA>_cost_rgba.tif     # RGBA visualization for tiles/MBTiles
#
# Usage:
#   AREA=yyz_downtown scripts/maps/make_costmap.sh [--yaml scripts/maps/cost_recipe.yaml] [--dem path/to.tif]
#
# Notes:
# - Masks are 0/1 Byte with NoData=0, NEAREST overviews only.
# - Slope is percent (-p).
# - Color ramp: transparent nv + nearest color entry (no halos).

AREA="${AREA:-}"
YAML="scripts/maps/cost_recipe.yaml"
DEM_IN=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --yaml) YAML="$2"; shift 2;;
    --dem)  DEM_IN="$2"; shift 2;;
    *) echo "Unknown arg: $1" >&2; exit 2;;
  esac
done

if [[ -z "$AREA" ]]; then
  echo "Set AREA=..." >&2; exit 2
fi

MAPS_DIR="maps"
BUILD_DIR="$MAPS_DIR/build"
COST_DIR="$MAPS_DIR/costmaps"
SRC_DIR="$MAPS_DIR/src"
TILES_DIR="tiles"

mkdir -p "$BUILD_DIR" "$COST_DIR" "$SRC_DIR"

DEM="${DEM_IN:-$BUILD_DIR/${AREA}_dtm1m.tif}"
OSM="$SRC_DIR/${AREA}_osm.osm"
SLOPE="$BUILD_DIR/${AREA}_slope.tif"
SLOPE_PNG="$BUILD_DIR/${AREA}_slope.png"

MASK_BLD="$BUILD_DIR/${AREA}_buildings_mask.tif"
MASK_ROAD="$BUILD_DIR/${AREA}_roads_mask.tif"
MASK_WATR="$BUILD_DIR/${AREA}_water_mask.tif"
MASK_PARK="$BUILD_DIR/${AREA}_parks_mask.tif"

COST_TIF="$COST_DIR/${AREA}_cost.tif"
COST_RGBA="$COST_DIR/${AREA}_cost_rgba.tif"

# --- Parse YAML (simple grep; keep keys first-level only) ---------------------
parse_y () {
  local key="$1"
  awk -F': *' -v k="$key" '$1==k{print $2; exit}' "$YAML"
}
SLOPE_MULT="$(parse_y slope_mult)"; : "${SLOPE_MULT:=2.0}"
PEN_BLD="$(parse_y building_penalty)"; : "${PEN_BLD:=200.0}"
PEN_ROAD="$(parse_y road_penalty)";   : "${PEN_ROAD:=80.0}"
PEN_WATR="$(parse_y water_penalty)";  : "${PEN_WATR:=500.0}"
PEN_PARK="$(parse_y park_penalty)";   : "${PEN_PARK:=20.0}"

echo "AREA=$AREA"
echo "DEM=$DEM"
echo "YAML=$YAML  (slope_mult=$SLOPE_MULT; bld=$PEN_BLD road=$PEN_ROAD water=$PEN_WATR park=$PEN_PARK)"

# --- Sanity -------------------------------------------------------------------
[[ -f "$DEM" ]] || { echo "Missing DEM: $DEM" >&2; exit 3; }

# Helper: zero mask on DEM grid
mk_zero_mask () {
  local dem="$1" out="$2"
  gdal_calc.py --quiet --overwrite -A "$dem" --calc="0*A+0" --type=Byte --outfile "$out"
  gdal_edit.py -a_nodata 0 "$out" >/dev/null
}

# Helper: burn vector into mask
burn_mask () {
  local vec="$1" out="$2"
  gdal_rasterize -burn 1 -at "$vec" "$out"
  gdaladdo -r NEAREST "$out" 2 4 8 >/dev/null 2>&1 || true
}

# Helper: force Byte 0/1 + clear aux stats
clean_mask () {
  local in="$1"
  gdal_translate -quiet -ot Byte -co TILED=YES -co COMPRESS=DEFLATE -co PREDICTOR=2 "$in" "${in}.tmp.tif"
  mv -f "${in}.tmp.tif" "$in"
  rm -f "${in}.aux.xml"
  gdalinfo -mm "$in" >/dev/null
}

# 1) Slope percent (+ PNG preview with fixed scale 0→15%) — explicitly Byte
if [[ ! -f "$SLOPE" ]]; then
  gdaldem slope -p "$DEM" "$SLOPE" -compute_edges
fi
gdal_translate -quiet -ot Byte -a_nodata 0 -scale 0 15 1 255 "$SLOPE" "$SLOPE_PNG"

# 2) Buildings mask (if not present, try to build from OSM)
if [[ ! -f "$MASK_BLD" ]]; then mk_zero_mask "$DEM" "$MASK_BLD"; fi
if [[ -f "$OSM" ]]; then
  TMP_GJ="$(mktemp -u --suffix=.geojson)"; trap 'rm -f "$TMP_GJ"' EXIT
  ogr2ogr -f GeoJSON "$TMP_GJ" "$OSM" multipolygons -where "building IS NOT NULL" || true
  if [[ -s "$TMP_GJ" ]]; then burn_mask "$TMP_GJ" "$MASK_BLD"; fi
fi
clean_mask "$MASK_BLD"

# 3) Roads mask (optional)
mk_zero_mask "$DEM" "$MASK_ROAD"
if [[ -f "$OSM" ]]; then
  TMP_GJ="$(mktemp -u --suffix=.geojson)"; trap 'rm -f "$TMP_GJ"' EXIT
  ogr2ogr -f GeoJSON "$TMP_GJ" "$OSM" lines -where "highway IS NOT NULL" || true
  if [[ -s "$TMP_GJ" ]]; then burn_mask "$TMP_GJ" "$MASK_ROAD"; fi
fi
clean_mask "$MASK_ROAD"

# 4) Water mask (optional)
mk_zero_mask "$DEM" "$MASK_WATR"
if [[ -f "$OSM" ]]; then
  TMP_W1="$(mktemp -u --suffix=.geojson)"; trap 'rm -f "'$TMP_W1'"' EXIT
  TMP_W2="$(mktemp -u --suffix=.geojson)"; trap 'rm -f "'$TMP_W2'"' EXIT
  # Common water areas (lakes, reservoirs, basins)
  ogr2ogr -f GeoJSON "$TMP_W1" "$OSM" multipolygons \n    -where "natural='water' OR landuse IN ('reservoir','basin')" || true
  # Wide rivers sometimes come as polygons tagged waterway=riverbank
  ogr2ogr -f GeoJSON "$TMP_W2" "$OSM" multipolygons \n    -where "waterway='riverbank'" || true
  [[ -s "$TMP_W1" ]] && burn_mask "$TMP_W1" "$MASK_WATR"
  [[ -s "$TMP_W2" ]] && burn_mask "$TMP_W2" "$MASK_WATR"
fi
clean_mask "$MASK_WATR"

# 5) Parks/green mask (optional)
mk_zero_mask "$DEM" "$MASK_PARK"
if [[ -f "$OSM" ]]; then
  TMP_GJ="$(mktemp -u --suffix=.geojson)"; trap 'rm -f "$TMP_GJ"' EXIT
  ogr2ogr -f GeoJSON "$TMP_GJ" "$OSM" multipolygons -where "leisure='park' OR landuse IN ('recreation_ground','grass')" || true
  if [[ -s "$TMP_GJ" ]]; then burn_mask "$TMP_GJ" "$MASK_PARK"; fi
fi
clean_mask "$MASK_PARK"

# 6) Combine to Float32 cost
#    cost = SLOPE_MULT*slope_percent + PEN_BLD*MB + PEN_ROAD*MR + PEN_WATR*MW + PEN_PARK*MP
gdal_calc.py --quiet --overwrite \
  -A "$SLOPE" -B "$MASK_BLD" -C "$MASK_ROAD" -D "$MASK_WATR" -E "$MASK_PARK" \
  --calc="$SLOPE_MULT*A + $PEN_BLD*B + $PEN_ROAD*C + $PEN_WATR*D + $PEN_PARK*E" \
  --NoDataValue=-9999 --type=Float32 --outfile "$COST_TIF"

# Convert to COG (deflate, tiled) and clear stale stats
gdal_translate -quiet -co TILED=YES -co COMPRESS=DEFLATE -co PREDICTOR=2 -co BIGTIFF=IF_NEEDED "$COST_TIF" "${COST_TIF}.tmp.tif"
mv -f "${COST_TIF}.tmp.tif" "$COST_TIF"
rm -f "${COST_TIF}.aux.xml"
gdaladdo -r AVERAGE "$COST_TIF" 2 4 8 >/dev/null 2>&1 || true
# Best-effort stats (quiet); Jammy GDAL sometimes samples overviews and warns if all NoData.
{ gdalinfo -mm   "$COST_TIF" >/dev/null 2>&1 || true; }
{ gdalinfo -stats "$COST_TIF" >/dev/null 2>&1 || true; }

# 7) RGBA visualization with transparent nv and nearest color entries
#    Scale 0→1500 → 1→255 for display (tweak upper bound if needed)
COLORTXT="$(mktemp)"; trap 'rm -f "$COLORTXT"' EXIT
cat >"$COLORTXT" <<'EOF'
nv 0 0 0 0
1  5 48 97 255
50 33 102 172 255
150 103 169 207 255
300 209 229 240 255
600 253 219 199 255
900 244 165 130 255
1200 214 96 77 255
1500 165 15 21 255
EOF

VRT8="$COST_DIR/${AREA}_cost_8bit.vrt"
{ gdal_translate -quiet -ot Byte -scale 0 1500 1 255 "$COST_TIF" "$VRT8" 2>/dev/null || \
  gdal_translate        -ot Byte -scale 0 1500 1 255 "$COST_TIF" "$VRT8"; }
gdal_edit.py -a_nodata 0 "$VRT8" >/dev/null 2>&1 || true

gdaldem color-relief -of GTiff -alpha -nearest_color_entry "$VRT8" "$COLORTXT" "$COST_RGBA"
echo "Wrote:"
echo "  $COST_TIF"
echo "  $COST_RGBA"
