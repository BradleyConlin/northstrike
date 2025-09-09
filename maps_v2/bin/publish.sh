#!/usr/bin/env bash
set -euo pipefail
AREA="${1:?area}"

# Resolve repo root and paths
ROOT="${ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
SRC="$ROOT/maps_v2/mbtiles/${AREA}_cost_color.mbtiles"
DST_DIR="$ROOT/artifacts/maps/mbtiles"

# Ensure source exists
test -f "$SRC" || { echo "ERROR: missing $SRC (build first)"; exit 2; }

# Publish
mkdir -p "$DST_DIR"
cp -f "$SRC" "$DST_DIR/"
OUT="$DST_DIR/$(basename "$SRC")"
echo "Published → $OUT"

# Summarize MBTiles metadata
gdalinfo "$OUT" | sed -n '1,120p'
