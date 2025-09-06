#!/usr/bin/env bash
set -euo pipefail
AREA="${AREA:-}"; : "${AREA:?Set AREA=...}"
: "${S:?Set S=...}"; : "${W:?Set W=...}"; : "${N:?Set N=...}"; : "${E:?Set E=...}"

OUT="maps/src/${AREA}_osm.osm"
QDATA="$(mktemp)"; trap 'rm -f "$QDATA"' EXIT

# Buildings + highways + basic water + leisure/landuse greens
cat >"$QDATA"<<EOF
[out:xml][timeout:120];
(
  way["building"](${S},${W},${N},${E});
  relation["building"](${S},${W},${N},${E});
  way["highway"](${S},${W},${N},${E});
  way["water"]( ${S},${W},${N},${E});
  relation["water"](${S},${W},${N},${E});
  way["natural"="water"](${S},${W},${N},${E});
  relation["natural"="water"](${S},${W},${N},${E});
  way["leisure"="park"](${S},${W},${N},${E});
  relation["leisure"="park"](${S},${W},${N},${E});
  way["landuse"~"recreation_ground|grass"](${S},${W},${N},${E});
  relation["landuse"~"recreation_ground|grass"](${S},${W},${N},${E});
);
(._;>;);
out body;
EOF

UA="northstrike/1.0 (contact: you@example.com)"
URL_PRIMARY="https://overpass-api.de/api/interpreter"
URL_BACKUP="https://overpass.kumi.systems/api/interpreter"

echo "Fetching OSM for AREA=$AREA → $OUT"
if ! curl -sS -A "$UA" --data-binary @"$QDATA" "$URL_PRIMARY" -o "$OUT"; then
  echo "Primary Overpass failed; trying backup..." >&2
  curl -sS -A "$UA" --data-binary @"$QDATA" "$URL_BACKUP" -o "$OUT"
fi
test -s "$OUT" || { echo "OSM fetch wrote empty file: $OUT" >&2; exit 2; }
echo "Wrote $OUT ($(wc -c <"$OUT") bytes)"
