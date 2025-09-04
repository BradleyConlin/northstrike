#!/usr/bin/env bash
set -euo pipefail
: "${AREA:?set AREA}"; : "${W:?}"; : "${S:?}"; : "${E:?}"; : "${N:?}"

mkdir -p maps/src
RAW_XML="$(mktemp)"
RAW_PBF="maps/src/${AREA}_raw.osm.pbf"
BLD_PBF="maps/src/${AREA}_buildings.osm.pbf"
GJ="maps/src/${AREA}_buildings.geojson"

# Overpass QL (bbox order: S,W,N,E)
Q='[out:xml][timeout:60];(way["building"]({{bbox}});relation["building"]({{bbox}}););(._;>;);out body;'
Q="${Q//'{{bbox}}'/${S},${W},${N},${E}}"

EP1="https://overpass.kumi.systems/api/interpreter"
EP2="https://overpass-api.de/api/interpreter"

# Prefer GET with url-encoded 'data' (mirrors often 400 POST)
curl -fsS --retry 3 --retry-delay 2 -A "northstrike/1.0" \
  --get --data-urlencode "data=${Q}" "$EP1" -o "$RAW_XML" \
|| curl -fsS --retry 3 --retry-delay 2 -A "northstrike/1.0" \
  --get --data-urlencode "data=${Q}" "$EP2" -o "$RAW_XML"

# Fail fast if the server returned an HTML error page
if head -c 256 "$RAW_XML" | grep -qi '<html'; then
  echo "Overpass returned an HTML error (rate limit/timeout). Try again later." >&2
  exit 1
fi

# Convert to PBF, filter buildings, export GeoJSON
osmium cat -F osm -O -o "$RAW_PBF" "$RAW_XML"
osmium tags-filter -O "$RAW_PBF" building -o "$BLD_PBF"
osmium export     -O "$BLD_PBF" -f geojson -o "$GJ"
echo "Wrote $GJ"
rm -f "$RAW_XML"
