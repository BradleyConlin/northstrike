#!/usr/bin/env bash
set -euo pipefail

AREA="${1:-yyz_downtown}"
DTM="maps/build/${AREA}_dtm1m.tif"
OSM="maps/src/${AREA}_osm.osm"

[[ -f "$DTM" ]] || { echo "ERR: missing $DTM"; exit 1; }
[[ -f "$OSM" ]] || { echo "ERR: missing $OSM"; exit 1; }

mkdir -p maps/build maps/masks maps/costmaps

# --- Read EPSG, pixel size & extent from DTM (Jammy-safe parsing) ---
EPSG=$(gdalsrsinfo -o epsg "$DTM" 2>/dev/null | sed -n 's/.*EPSG:\([0-9]\+\).*/\1/p' | head -n1)
[[ -z "$EPSG" ]] && EPSG=$(gdalinfo "$DTM" | grep -o 'EPSG:[0-9]\+' | head -n1 | cut -d: -f2)
[[ -z "$EPSG" ]] && EPSG=32617

read PSX PSY < <(gdalinfo "$DTM" | sed -n 's/.*Pixel Size = (\([^,]*\), \([^)]*\)).*/\1 \2/p')
TRX=$(awk -v v="$PSX" 'BEGIN{print (v<0)?-v:v}')
TRY=$(awk -v v="$PSY" 'BEGIN{print (v<0)?-v:v}')

read ULX ULY < <(gdalinfo "$DTM" | sed -n 's/.*Upper Left  (\([^,]*\), \([^)]*\)).*/\1 \2/p')
read LRX LRY < <(gdalinfo "$DTM" | sed -n 's/.*Lower Right (\([^,]*\), \([^)]*\)).*/\1 \2/p')
MINX="$ULX"; MAXY="$ULY"; MAXX="$LRX"; MINY="$LRY"

# --- 1) Slope (%)
SLOPE="maps/build/${AREA}_slope_pct.tif"
gdaldem slope -p "$DTM" "$SLOPE" -compute_edges

# Common creation options
CO=(-co TILED=YES -co COMPRESS=DEFLATE)

# --- 2) Rasterize OSM masks aligned to DTM ---
# Buildings: multipolygons with building IS NOT NULL
B="maps/masks/${AREA}_buildings_mask.tif"
gdal_rasterize -ot Byte -a_nodata 0 -init 0 -at \
  -te "$MINX" "$MINY" "$MAXX" "$MAXY" -tr "$TRX" "$TRY" -a_srs "EPSG:${EPSG}" \
  -l multipolygons -where "building IS NOT NULL" "${OSM}" "${B}" "${CO[@]}"

# Roads: lines with highway IS NOT NULL
R="maps/masks/${AREA}_roads_mask.tif"
gdal_rasterize -ot Byte -a_nodata 0 -init 0 -at \
  -te "$MINX" "$MINY" "$MAXX" "$MAXY" -tr "$TRX" "$TRY" -a_srs "EPSG:${EPSG}" \
  -l lines -where "highway IS NOT NULL" "${OSM}" "${R}" "${CO[@]}"

# Water: multipolygons natural='water' OR landuse IN (...) OR waterway='riverbank'
W="maps/masks/${AREA}_water_mask.tif"
gdal_rasterize -ot Byte -a_nodata 0 -init 0 -at \
  -te "$MINX" "$MINY" "$MAXX" "$MAXY" -tr "$TRX" "$TRY" -a_srs "EPSG:${EPSG}" \
  -l multipolygons -where "natural='water' OR landuse IN ('reservoir','basin') OR waterway='riverbank'" \
  "${OSM}" "${W}" "${CO[@]}"

# Parks: multipolygons leisure='park' OR landuse in commons
P="maps/masks/${AREA}_parks_mask.tif"
gdal_rasterize -ot Byte -a_nodata 0 -init 0 -at \
  -te "$MINX" "$MINY" "$MAXX" "$MAXY" -tr "$TRX" "$TRY" -a_srs "EPSG:${EPSG}" \
  -l multipolygons -where "leisure='park' OR landuse IN ('recreation_ground','grass','park')" \
  "${OSM}" "${P}" "${CO[@]}"

# --- 3) Combine to Float32 cost (NoData only where DTM is NoData)
# Tunable weights
SLOPE_MULT=2.0
BUILDING=200.0
ROAD=-40.0
WATER=500.0
PARK=20.0

COST="maps/costmaps/${AREA}_cost.tif"
gdal_calc.py \
  -A "$DTM" -B "$SLOPE" -C "$B" -R "$R" -W "$W" -P "$P" \
  --calc="where(A!=-9999, ${SLOPE_MULT}*B + ${BUILDING}*C + ${ROAD}*R + ${WATER}*W + ${PARK}*P, -9999)" \
  --type=Float32 --NoDataValue=-9999 --outfile "$COST" "${CO[@]}"

echo "Wrote $COST"
