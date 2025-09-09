#!/usr/bin/env bash
set -euo pipefail
IN="${1:?input RGBA 3857 GeoTIFF}"; NAME="${2:-$(basename "${IN%.tif}")}"
OUT_DIR="artifacts/maps/mbtiles"; mkdir -p "$OUT_DIR"
OUT="$OUT_DIR/${NAME}.mbtiles"
echo "[*] Building $OUT from $IN"
gdal_translate -of MBTILES "$IN" "$OUT"
gdaladdo -r nearest "$OUT" 2 4 8 16 32
echo "[*] Done → $OUT"; gdalinfo "$OUT" | sed -n '1,60p'
