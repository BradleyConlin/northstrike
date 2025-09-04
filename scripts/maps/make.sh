#!/usr/bin/env bash
set -euo pipefail
# Usage:
#   scripts/maps/make.sh dem AREA S W N E
#   scripts/maps/make.sh buildings AREA S W N E
#   scripts/maps/make.sh costmap AREA
cmd="${1:-}"; shift || true
case "$cmd" in
  dem)
    AREA="$1"; S="$2"; W="$3"; N="$4"; E="$5"
    scripts/maps/fetch_hrdem_1m_vrt.sh "$AREA" "$S" "$W" "$N" "$E"
    ;;
  buildings)
    AREA="$1"; S="$2"; W="$3"; N="$4"; E="$5"
    scripts/maps/fetch_osm_buildings.sh "$AREA" "$S" "$W" "$N" "$E"
    ;;
  costmap)
    AREA="${1:?AREA required}"
    DEM="maps/build/${AREA}_dtm1m.tif" scripts/maps/make_costmap.sh
    ;;
  *)
    echo "Usage: $0 {dem|buildings|costmap} ..." >&2; exit 2;;
esac
