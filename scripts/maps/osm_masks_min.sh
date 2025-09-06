#!/usr/bin/env bash
set -euo pipefail
AREA="${1:?AREA required}"

DTM="maps/build/${AREA}_dtm1m.tif"
OSM="maps/src/${AREA}_osm.osm"
TMP="maps/build/osm_tmp_${AREA}"
mkdir -p maps/masks "$TMP"

[[ -f "$DTM" ]] || { echo "ERR: missing $DTM"; exit 1; }

# 1) Create zero Byte masks aligned to the DTM (no NoData)
mk_zero() {
  local out="$1"
  gdal_calc.py -A "$DTM" --calc="0" \
    --type=Byte --overwrite \
    --co TILED=YES --co COMPRESS=DEFLATE \
    --outfile "$out" >/dev/null
}

for m in buildings roads water parks; do
  mk_zero "maps/masks/${AREA}_${m}_mask.tif"
  rm -f "maps/masks/${AREA}_${m}_mask.tif.aux.xml" || true
done

# 2) If OSM is absent, keep masks as all-zero (safe)
if [[ ! -f "$OSM" ]]; then
  echo "NOTE: $OSM missing; masks remain zero."
  exit 0
fi

# 3) Extract polygons that commonly exist in 'multipolygons'
rm -f "$TMP"/buildings.geojson "$TMP"/water.geojson "$TMP"/parks.geojson

# Buildings
ogr2ogr -skipfailures -f GeoJSON "$TMP/buildings.geojson" "$OSM" multipolygons \
  -where "building IS NOT NULL" || true

# Water (robust subset)
ogr2ogr -skipfailures -f GeoJSON "$TMP/water.geojson" "$OSM" multipolygons \
  -where "natural='water' OR landuse IN ('reservoir','basin')" || true

# Parks
ogr2ogr -skipfailures -f GeoJSON "$TMP/parks.geojson" "$OSM" multipolygons \
  -where "leisure='park'" || true

# 4) Burn polygons into the existing masks (no -tr/-ts, no -l)
burn() {
  local src="$1" out="$2"
  [[ -s "$src" ]] || return 0
  gdal_rasterize -burn 1 -at "$src" "$out"
  rm -f "${out}.aux.xml" || true
}

burn "$TMP/buildings.geojson" "maps/masks/${AREA}_buildings_mask.tif"
burn "$TMP/water.geojson"     "maps/masks/${AREA}_water_mask.tif"
burn "$TMP/parks.geojson"     "maps/masks/${AREA}_parks_mask.tif"
# roads left zero for now (we’ll add line-buffering later)

echo "Masks ready under maps/masks/ (Byte 0/1, no NoData, DTM-aligned)."
