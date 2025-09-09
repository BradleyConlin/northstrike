#!/usr/bin/env bash
set -euo pipefail
ROOT="${ROOT:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
V2="$ROOT/maps_v2"
docker rm -f ns-mbtiles-8001 2>/dev/null || true
docker run -d --name ns-mbtiles-8001 -p 8001:8000 \
  -v "$V2/mbtiles:/tilesets" ghcr.io/consbio/mbtileserver:latest
echo "Preview: http://127.0.0.1:8001/services/toronto_cost_color/map"
