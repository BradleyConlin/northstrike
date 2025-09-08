#!/usr/bin/env bash
set -euo pipefail
# fetch_dem_cop30.sh <AOI_TAG> <S> <W> <N> <E>
# Requires: OPENTOPO_API_KEY env var

AOI="${1:-}"; S="${2:-}"; W="${3:-}"; N="${4:-}"; E="${5:-}"
[[ -z "${AOI}${S}${W}${N}${E}" ]] && { echo "Usage: $0 <AOI_TAG> <S> <W> <N> <E>"; exit 2; }

API="${OPENTOPO_API_KEY:-}"
[[ -z "$API" ]] && { echo "ERROR: Set OPENTOPO_API_KEY first"; exit 3; }

ROOT="$(pwd)"; BUILD="$ROOT/maps/build"; mkdir -p "$BUILD"
RAW="$BUILD/${AOI}_cop30_raw.tif"
OUT="$BUILD/${AOI}_dtm_wgs84_clip.tif"

URL="https://portal.opentopography.org/API/globaldem?demtype=COP30&south=${S}&north=${N}&west=${W}&east=${E}&outputFormat=GTiff&API_Key=${API}"

echo "Fetching COP30 → $RAW"
curl -sS -L --fail -A "northstrike/0.1 (+https://github.com/BradleyConlin/northstrike)" "$URL" -o "$RAW"

# Validate it’s a readable GeoTIFF
gdalinfo "$RAW" >/dev/null

# Warp/clip to exact bbox in EPSG:4326
gdalwarp -t_srs EPSG:4326 -r bilinear -overwrite -te "$W" "$S" "$E" "$N" "$RAW" "$OUT"
echo "DEM ready: $OUT"
