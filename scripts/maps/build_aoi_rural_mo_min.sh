#!/usr/bin/env bash
set -euo pipefail
REPO=~/dev/northstrike; cd "$REPO"
export OSM_PBF_URL="https://download.geofabrik.de/north-america/us/missouri-latest.osm.pbf"
AOI=aoi_rural_mo
S=37.6593; W=-91.1989; N=37.7674; E=-91.0621
DEM="maps/build/aoi_rural_mo_dtm_wgs84_clip.tif"
bash scripts/maps/build_cost_from_osm.sh "$AOI" "$S" "$W" "$N" "$E" "$DEM"
