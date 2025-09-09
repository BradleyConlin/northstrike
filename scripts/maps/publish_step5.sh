#!/usr/bin/env bash
set -euo pipefail
REPO="${REPO:-$(pwd)}"
PUB="$REPO/artifacts/publish"
MBT="$REPO/artifacts/maps/mbtiles"
VIEW="$REPO/viewer/mbtiles_overlay.html"
mkdir -p "$PUB/tiles" "$PUB/viewer"
shopt -s nullglob
copied=0
for f in "$MBT"/*_cost_color.mbtiles; do
  b="$(basename "$f")"
  cp -f "$f" "$PUB/tiles/$b"
  copied=$((copied+1))
done
cp -f "$VIEW" "$PUB/viewer/"
( cd "$PUB" && \
  { find . -type f -print0 | xargs -0 sha256sum > SHA256SUMS.txt; } )
echo "[publish_step5] Copied $copied MBTiles -> $PUB/tiles"
echo "[publish_step5] Viewer copied -> $PUB/viewer/mbtiles_overlay.html"
echo "[publish_step5] Checksums -> $PUB/SHA256SUMS.txt"
