#!/usr/bin/env bash
set -euo pipefail
NAME="ns-mbtiles-8001"; PORT=8001
DIR1="$(pwd)/artifacts/maps/mbtiles"
DIR2="$(pwd)/maps_v2/mbtiles"
docker rm -f "$NAME" 2>/dev/null || true
docker run -d --name "$NAME" -p ${PORT}:8000 \
  -e TILE_DIR="/tiles1,/tiles2" \
  -v "$DIR1:/tiles1:ro" -v "$DIR2:/tiles2:ro" \
  ghcr.io/consbio/mbtileserver:latest
echo "→ Services: http://127.0.0.1:${PORT}/services"
