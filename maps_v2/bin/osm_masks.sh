#!/usr/bin/env bash
set -euo pipefail
# Usage: osm_masks.sh <aoi> <S> <W> <N> <E> <dem_utm.tif> <mask_out.tif>

AOI="${1}"; S="${2}"; W="${3}"; N="${4}"; E="${5}"
DEM="${6}"; MASK_OUT="${7}"

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
AOI_DIR="${ROOT}/build/${AOI}"
mkdir -p "${AOI_DIR}"

OSM_XML="${AOI_DIR}/${AOI}_buildings.osm"
GPKG="${AOI_DIR}/${AOI}_buildings.gpkg"

echo "[OSM] Fetch buildings via Overpass"
Q="[out:xml][timeout:120];(way[\"building\"](${S},${W},${N},${E});relation[\"building\"](${S},${W},${N},${E}););(._;>;);out body;"
if ! curl --globoff -sS 'https://overpass-api.de/api/interpreter' \
      --data-urlencode "data=${Q}" -o "${OSM_XML}"; then
  echo "[OSM] Primary failed; trying fallback…"
  curl --globoff -sS 'https://overpass.kumi.systems/api/interpreter' \
      --data-urlencode "data=${Q}" -o "${OSM_XML}"
fi

# Vectorize → GPKG with a predictable layer name
echo "[OSM] Vectorize footprints → GeoPackage (layer=buildings)"
ogr2ogr -q -f GPKG "${GPKG}" "${OSM_XML}" multipolygons \
       -where "building IS NOT NULL" \
       -nln buildings -overwrite -skipfailures -progress -gt 5000 || true

# Count features (may be 0)
FEATURES=$(ogrinfo -so "${GPKG}" buildings 2>/dev/null | awk '/Feature Count:/ {print $3+0}' || echo 0)
echo "[OSM] buildings features = ${FEATURES}"

echo "[OSM] Seed an empty, DEM-aligned mask (Byte, nodata=0)"
gdal_calc.py -A "${DEM}" --calc="A*0" \
  --type=Byte --NoDataValue=0 --overwrite \
  --co=TILED=YES --co=COMPRESS=DEFLATE --co=BIGTIFF=IF_NEEDED \
  --quiet --outfile="${MASK_OUT}"

if [ "${FEATURES}" -gt 0 ]; then
  echo "[OSM] Burn footprints into mask (value=1)"
  gdal_rasterize -q -burn 1 -at -l buildings "${GPKG}" "${MASK_OUT}"
else
  echo "[OSM] No buildings → leaving mask all zeros"
fi

echo "OK: ${MASK_OUT}"
