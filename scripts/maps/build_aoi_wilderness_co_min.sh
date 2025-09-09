#!/usr/bin/env bash
set -euo pipefail
REPO=~/dev/northstrike; cd "$REPO"
export OSM_PBF_URL="https://download.geofabrik.de/north-america/us/colorado-latest.osm.pbf"
AOI=aoi_wilderness_co
S=37.28836786485658; W=-107.81322624272447
N=37.66191854515221; E=-107.23919059819323
DEM="maps/build/aoi_wilderness_co_dtm_wgs84_clip.tif"
bash scripts/maps/build_cost_from_osm.sh "$AOI" "$S" "$W" "$N" "$E" "$DEM"
