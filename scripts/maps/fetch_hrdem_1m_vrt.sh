#!/usr/bin/env bash
set -euo pipefail
# Usage:
#   scripts/maps/fetch_hrdem_1m_vrt.sh AREA S W N E
# Example:
#   scripts/maps/fetch_hrdem_1m_vrt.sh yyz_downtown 43.63 -79.42 43.70 -79.31
# Output: maps/build/${AREA}_dtm1m.tif  (UTM-projected, 1m)

if [ "$#" -ne 5 ]; then
  echo "Usage: $0 AREA S W N E" >&2
  exit 1
fi

AREA="$1"; S="$2"; W="$3"; N="$4"; E="$5"
OUT_DIR="maps/build"
OUT_TIF="${OUT_DIR}/${AREA}_dtm1m.tif"
TMP_VRT="${OUT_DIR}/${AREA}_crop_wgs84.vrt"
ASSET="https://canelevation-dem.s3.ca-central-1.amazonaws.com/hrdem-mosaic-1m/8_2-mosaic-1m-dtm.tif"
ASSET_VSICURL="/vsicurl/${ASSET}"
mkdir -p "$OUT_DIR"

# Compute UTM zone from bbox center lon
LON_CENTER="$(awk -v a="$W" -v b="$E" 'BEGIN{print (a+b)/2.0}')"
ZONE="$(python3 - "$LON_CENTER" <<'PY'
import sys,math
lon=float(sys.argv[1])
zone=int(math.floor((lon+180)/6)+1)
print(zone)
PY
)"
UTM_EPSG="326${ZONE}"

echo "[i] Source asset: $ASSET"
echo "[i] Temp crop (WGS84): $TMP_VRT"
echo "[i] Target CRS: EPSG:${UTM_EPSG}"
echo "[i] Final out: $OUT_TIF"

# Stage 1: crop to bbox in WGS84 into a small VRT (no big write yet)
# Note: -te expects minX minY maxX maxY; -te_srs ensures those are EPSG:4326
gdalwarp -of VRT \
  -t_srs EPSG:4326 \
  -te_srs EPSG:4326 -te "$W" "$S" "$E" "$N" \
  -r bilinear \
  "$ASSET_VSICURL" "$TMP_VRT"

# Stage 2: reproject that tiny VRT to UTM at 1 m resolution and write GTiff
gdalwarp -t_srs "EPSG:${UTM_EPSG}" \
  -tr 1 1 -r bilinear -overwrite \
  -dstnodata -9999 \
  -co BIGTIFF=IF_NEEDED -co TILED=YES -co COMPRESS=DEFLATE \
  "$TMP_VRT" "$OUT_TIF"

# Minimal verification
echo "[ok] DEM written: $OUT_TIF"
gdalinfo -stats "$OUT_TIF" | sed -n '1,60p'
