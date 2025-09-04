#!/usr/bin/env bash
set -euo pipefail
AREA="${AREA:-area1}"
DEM="maps/src/${AREA}_dem.tif"
BLD_VECT="${BLD_VECT:-maps/src/${AREA}_buildings.geojson}"
OUTDIR="maps/build/${AREA}"
COST="maps/costmaps/${AREA}_cost.tif"
mkdir -p "$OUTDIR" maps/costmaps

if [[ ! -f "$DEM" ]]; then echo "Missing $DEM"; exit 2; fi
if [[ ! -f "$BLD_VECT" ]]; then echo "Missing $BLD_VECT"; exit 2; fi

echo "[1/4] slope from DEM"
gdaldem slope "$DEM" "$OUTDIR/slope.tif" -s 1.0

echo "[2/4] rasterize buildings to DEM grid"
# Align to DEM georeferencing
gdal_rasterize -burn 1 -a_nodata 0 -te $(gdalinfo "$DEM" | awk '/Lower Left|Upper Right/ {gsub(/[(),]/,""); if ($1=="Lower") {xmin=$3; ymin=$4} else {xmax=$3; ymax=$4}} END {print xmin, ymin, xmax, ymax}') \
  -tr $(gdalinfo "$DEM" | awk -F'[(), ]+' '/Pixel Size/ {print ($6<0)?-$5:$5, ($6<0)?-$6:$6}') \
  -ot Byte -init 0 "$BLD_VECT" "$OUTDIR/buildings.tif"

echo "[3/4] combine slope + buildings to cost (buildings=1000, slope cost = 10*(s/45)^2 + 1)"
gdal_calc.py --quiet \
  -A "$OUTDIR/slope.tif" -B "$OUTDIR/buildings.tif" \
  --calc="where(B==1, 1000, minimum(1000, 10*(A/45.0)*(A/45.0) + 1))" \
  --NoDataValue=0 --outfile="$COST" --type=Float32

echo "[4/4] done -> $COST"
