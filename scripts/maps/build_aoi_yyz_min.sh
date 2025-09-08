#!/usr/bin/env bash
set -euo pipefail
REPO=~/dev/northstrike; cd "$REPO"
export OSM_PBF_URL="https://download.geofabrik.de/north-america/canada/ontario-latest.osm.pbf"
AOI=yyz_downtown
S=43.6284246884319344; W=-79.42183462233241
N=43.70157325516256;  E=-79.30803385824855
DEM="maps/build/yyz_downtown_dtm_wgs84_clip.tif"
bash scripts/maps/build_cost_from_osm.sh "$AOI" "$S" "$W" "$N" "$E" "$DEM"
