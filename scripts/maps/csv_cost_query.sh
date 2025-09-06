#!/usr/bin/env bash
set -euo pipefail
if [ "$#" -lt 2 ]; then
  echo "Usage: $0 AREA input.csv [out.csv]" >&2
  exit 1
fi

AREA="$1"; IN="$2"; OUT="${3:-maps/reports/${AREA}_cost_query.csv}"
RASTER="maps/costmaps/${AREA}_cost.tif"

# Discover raster EPSG (fallback UTM17N)
EPSG=$(gdalsrsinfo -o epsg "$RASTER" 2>/dev/null | sed -n 's/.*EPSG:\([0-9]\+\).*/\1/p' | head -n1)
[ -z "$EPSG" ] && EPSG=$(gdalinfo "$RASTER" | grep -o 'EPSG:[0-9]\+' | head -n1 | cut -d: -f2)
[ -z "$EPSG" ] && EPSG=32617

mkdir -p "$(dirname "$OUT")"
echo "lat,lon,cost" > "$OUT"

tail -n +2 "$IN" | while IFS=, read -r c1 c2 _; do
  # Decide if inputs look like degrees
  if awk -v lat="$c1" -v lon="$c2" 'BEGIN{exit ! (lat>=-90 && lat<=90 && lon>=-180 && lon<=180)}'; then
    LAT="$c1"; LON="$c2"
  else
    # Treat as X/Y in raster CRS → convert to lon/lat
    read LON LAT _ < <(echo "$c1 $c2" | gdaltransform -s_srs EPSG:$EPSG -t_srs EPSG:4326)
  fi

  val=$(gdallocationinfo -wgs84 -valonly "$RASTER" "$LON" "$LAT" 2>/dev/null || echo "")
  [ -z "$val" ] && val="NaN"
  [ "$val" = "-9999" ] && val="NaN"
  echo "$LAT,$LON,$val" >> "$OUT"
done

echo "Wrote $OUT"
