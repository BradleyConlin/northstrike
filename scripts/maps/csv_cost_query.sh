#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -lt 2 ] ; then
  echo "Usage: $0 AREA input.csv [out.csv]" >&2
  exit 1
fi
AREA="$1"; IN="$2"; OUT="${3:-maps/reports/${AREA}_cost_query.csv}"
RASTER="maps/costmaps/${AREA}_cost.tif"
mkdir -p "$(dirname "$OUT")"
echo "lat,lon,cost" > "$OUT"
tail -n +2 "$IN" | while IFS=, read -r lat lon; do
  val=$(gdallocationinfo -wgs84 -valonly "$RASTER" "$lon" "$lat" 2>/dev/null || echo "NaN")
  echo "$lat,$lon,$val" >> "$OUT"
done
echo "Wrote $OUT"
