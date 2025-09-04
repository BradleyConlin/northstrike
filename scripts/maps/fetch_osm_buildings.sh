#!/usr/bin/env bash
set -euo pipefail
# Usage: scripts/maps/fetch_osm_buildings.sh AREA S W N E
AREA="$1"; S="$2"; W="$3"; N="$4"; E="$5"
OUT="maps/src/${AREA}_buildings.geojson"
TMP="maps/src/${AREA}_osm_buildings.osm"
mkdir -p maps/src

# Overpass expects bbox S,W,N,E. Ask for OSM XML (best for GDAL's OSM driver).
read -r -d '' QL <<EOF
[out:xml][timeout:90];
(
  way["building"]($S,$W,$N,$E);
  relation["building"]($S,$W,$N,$E);
);
out body;
>;
out skel qt;
EOF

UA="NorthstrikeMaps/1.0 (github.com/BradleyConlin/northstrike)"
URL_PRIMARY="https://overpass-api.de/api/interpreter"
URL_FALLBACK="https://overpass.kumi.systems/api/interpreter"

# Download XML to file (primary, then fallback on failure)
if ! curl -fsSL -A "$UA" -G --data-urlencode "data=$QL" "$URL_PRIMARY" -o "$TMP"; then
  echo "[warn] Overpass primary failed; trying fallback…" >&2
  curl -fsSL -A "$UA" -G --data-urlencode "data=$QL" "$URL_FALLBACK" -o "$TMP"
fi

# Quick sanity check
if [ ! -s "$TMP" ]; then
  echo "[err] Empty Overpass response ($TMP). Try a slightly larger bbox or re-run later." >&2
  exit 2
fi

# Convert to GeoJSON: OSM driver exposes layers; buildings are in 'multipolygons'.
# Filter to features that actually have a 'building' tag.
ogr2ogr -f GeoJSON "$OUT" "$TMP" multipolygons -where "building IS NOT NULL" -oo USE_CUSTOM_INDEXING=NO

# Optional: remove temp file (comment next line if you want to keep the raw OSM)
rm -f "$TMP"

echo "[ok] Buildings → $OUT"
