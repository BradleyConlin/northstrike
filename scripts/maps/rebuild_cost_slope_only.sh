#!/usr/bin/env bash
set -euo pipefail
set -x

AREA="${1:-yyz_downtown}"
DTM="maps/build/${AREA}_dtm1m.tif"
SLOPE="maps/build/${AREA}_slope_pct.tif"
COST="maps/costmaps/${AREA}_cost.tif"

[[ -f "$DTM" ]] || { echo "ERR: missing $DTM"; exit 1; }
mkdir -p maps/build maps/costmaps maps/reports

# 0) Kill stale outputs (and aux files) so nothing is read-only/cached
rm -f "$SLOPE" "$SLOPE.aux.xml" "$COST" "$COST.aux.xml"

# 1) Recompute slope (%)
gdaldem slope -p "$DTM" "$SLOPE" -compute_edges

# 2) Fresh Float32 cost = 2.0 * slope, masked only by DTM validity
gdal_calc.py -A "$SLOPE" -B "$DTM" \
  --calc="(B!=-9999)*2.0*A + (B==-9999)*(-9999)" \
  --type=Float32 --NoDataValue=-9999 --overwrite \
  --co TILED=YES --co COMPRESS=DEFLATE \
  --outfile "$COST"

# 3) Non-writing min/max probe + a known downtown sample
gdalinfo -mm "$COST" | sed -n '1,80p'
gdallocationinfo -wgs84 -valonly "$COST" -79.3839 43.6535 || true

# 4) Make 5 inside points and query them
python scripts/maps/make_inside_points.py "$AREA" 5
python scripts/maps/csv_cost_query_cli.py "$AREA" "maps/reports/${AREA}_inside_latlon.csv"
column -s, -t "maps/reports/${AREA}_cost_query.csv" | sed -n '1,12p'
