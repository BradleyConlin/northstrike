#!/usr/bin/env bash
set -euo pipefail

AOI="${1:?name}"; S="${2:?}"; W="${3:?}"; N="${4:?}"; E="${5:?}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
BIN_DIR="$ROOT/bin"
RAMPS="$ROOT/ramps"
OUTDIR="$ROOT/build/$AOI"
MBTILES_DIR="$ROOT/mbtiles"
mkdir -p "$OUTDIR" "$MBTILES_DIR"

LON_C=$(awk -v a="$W" -v b="$E" 'BEGIN{printf "%.6f",(a+b)/2.0}')
ZONE=$(awk -v lon="$LON_C" 'BEGIN{print int((lon+180.0)/6.0)+1}')
EPSG="EPSG:326$ZONE"
echo "[i] Using UTM $EPSG for lon=$LON_C (zone=$ZONE)"

DEM_TMP="$OUTDIR/${AOI}_dtm_tmp.tif"
DEM_UTM="$OUTDIR/${AOI}_dtm1m_utm.tif"
SLOPE="$OUTDIR/${AOI}_slope_pct.tif"
MASK_BUILD="$OUTDIR/${AOI}_buildings_mask.tif"
COST_F32="$OUTDIR/${AOI}_cost_f32.tif"
BYTE_0400="$OUTDIR/${AOI}_0_400_byte.tif"
COLOR_UTM="$OUTDIR/${AOI}_cost_color_utm.tif"
COLOR_3857="$OUTDIR/${AOI}_cost_color_3857.tif"
MBTILES="$MBTILES_DIR/${AOI}_cost_color.mbtiles"
RAMP="$RAMPS/cost_ramp_default.txt"

# 1) DEM (download COP30 only if missing)
if [[ ! -f "$DEM_UTM" ]]; then
  echo "[1/6] DEM download (COP30) and warp → UTM @ 1 m"
  : "${OPENTOPO_API_KEY:?OPENTOPO_API_KEY must be set for COP30 fetch}"
  curl --fail -L "https://portal.opentopography.org/API/globaldem?demtype=COP30&south=$S&north=$N&west=$W&east=$E&outputFormat=GTiff&API_Key=$OPENTOPO_API_KEY" -o "$DEM_TMP"
  gdalwarp -overwrite -t_srs "$EPSG" -te_srs EPSG:4326 -te "$W" "$S" "$E" "$N" \
           -tr 1 1 -r bilinear -dstnodata -9999 \
           -co TILED=YES -co COMPRESS=DEFLATE -co BIGTIFF=IF_NEEDED \
           "$DEM_TMP" "$DEM_UTM" -q
else
  echo "[1/6] DEM present → $DEM_UTM"
fi

# 2) Slope
echo "[2/6] Slope (%) from metric DEM"
gdaldem slope -p "$DEM_UTM" "$SLOPE" -of GTiff \
       -co TILED=YES -co COMPRESS=DEFLATE -co BIGTIFF=IF_NEEDED -q

# 3) Buildings mask (graceful empty fallback)
echo "[3/6] OSM buildings → mask (DEM-aligned)"
if ! "$BIN_DIR/osm_masks.sh" "$AOI" "$S" "$W" "$N" "$E" "$DEM_UTM" "$MASK_BUILD"; then
  echo "[OSM] mask build failed, creating empty mask"
  gdal_calc.py -A "$DEM_UTM" --calc="0*A*0" --type=Byte --NoDataValue=0 \
               --co=TILED=YES --co=COMPRESS=DEFLATE --co=BIGTIFF=IF_NEEDED \
               --overwrite --outfile="$MASK_BUILD" --quiet
fi

# 4) Cost (pre-delete + overwrite = fix the read-only issue)
echo "[4/6] Compute cost = 2*slope + 200*buildings"
rm -f "$COST_F32"
gdal_calc.py -A "$SLOPE" -B "$MASK_BUILD" \
             --type=Float32 --NoDataValue=-9999 --overwrite \
             --calc="2*A + 200*B" \
             --co=TILED=YES --co=COMPRESS=DEFLATE --co=BIGTIFF=IF_NEEDED \
             --overwrite --outfile="$COST_F32" --quiet

# 5) Colorize
echo "[5/6] Style → color overlay"
gdal_translate -ot Byte -scale 0 400 1 255 "$COST_F32" "$BYTE_0400" -q
gdaldem color-relief -alpha "$BYTE_0400" "$RAMP" "$COLOR_UTM" -q
gdalwarp -overwrite -t_srs EPSG:3857 -r near -dstalpha \
         -co TILED=YES -co COMPRESS=DEFLATE -co BIGTIFF=IF_NEEDED \
         "$COLOR_UTM" "$COLOR_3857" -q

# 6) MBTiles
echo "[6/6] MBTiles publish"
rm -f "$MBTILES"
gdal_translate -of MBTILES "$COLOR_3857" "$MBTILES" -q
gdaladdo -r nearest "$MBTILES" 2 4 8 16 32 -q
echo "OK: $MBTILES"
