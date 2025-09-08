#!/usr/bin/env bash
set -euo pipefail
# pbf_clip_and_filter.sh <AOI_TAG> <PBF_URL> <S> <W> <N> <E>
# Outputs: maps/masks/<AOI_TAG>_filtered.osm.pbf

AOI="${1:-}"; PBF_URL="${2:-}"; S="${3:-}"; W="${4:-}"; N="${5:-}"; E="${6:-}"
[[ -z "${AOI}${PBF_URL}${S}${W}${N}${E}" ]] && { echo "Usage: $0 <AOI> <PBF_URL> <S> <W> <N> <E>"; exit 2; }

ROOT="$(pwd)"
MASKS="$ROOT/maps/masks"; mkdir -p "$MASKS"
SRC="$MASKS/${AOI}_source.osm.pbf"
BBOX="$MASKS/${AOI}_bbox.osm.pbf"
OUT="$MASKS/${AOI}_filtered.osm.pbf"

UA="northstrike/0.1 (+https://github.com/BradleyConlin/northstrike)"

# 1) Fetch regional PBF (cached)
if [[ ! -f "$SRC" ]]; then
  echo "[pbf] download → $SRC"
  curl -L --fail -sS -A "$UA" "$PBF_URL" -o "$SRC"
fi

# 2) BBox extract (fast, small)
echo "[pbf] bbox extract → $BBOX"
osmium extract -b ${W},${S},${E},${N} "$SRC" -o "$BBOX" --overwrite

# 3) Keep only what we need (n=nodes, w=ways, r=relations)
#   buildings, natural=water, waterway=riverbank, water in lake/pond/reservoir/basin
echo "[pbf] tags filter → $OUT"
osmium tags-filter "$BBOX" -o "$OUT" --overwrite \
  nwr building \
  nwr natural=water \
  nwr waterway=riverbank \
  nwr water=lake \
  nwr water=pond \
  nwr water=reservoir \
  nwr water=basin

echo "$OUT"
