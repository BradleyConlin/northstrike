#!/usr/bin/env bash
set -euo pipefail

dem_bbox_wgs84() {
  local dem="$1"
  if gdalinfo -json "$dem" | jq -e '.wgs84Extent' >/dev/null 2>&1; then
    # four numbers: W S E N (tab-sep)
    read -r W S E N < <(gdalinfo -json "$dem" | jq -r '
      .wgs84Extent.coordinates[0] as $p
      | [ ($p|map(.[0])|min),
          ($p|map(.[1])|min),
          ($p|map(.[0])|max),
          ($p|map(.[1])|max) ] | @tsv')
  else
    # fallback: transform corners from DEM CRS -> WGS84
    local epsg ulx uly urx ury llx lly lrx lry
    epsg=$(gdalsrsinfo -o epsg "$dem" | sed -n 's/.*\(EPSG:[0-9]\+\).*/\1/p' | head -n1)
    read -r ulx uly < <(gdalinfo -json "$dem" | jq -r '.cornerCoordinates.upperLeft|@tsv')
    read -r urx ury < <(gdalinfo -json "$dem" | jq -r '.cornerCoordinates.upperRight|@tsv')
    read -r llx lly < <(gdalinfo -json "$dem" | jq -r '.cornerCoordinates.lowerLeft|@tsv')
    read -r lrx lry < <(gdalinfo -json "$dem" | jq -r '.cornerCoordinates.lowerRight|@tsv')
    read -r ULlon ULlat < <(printf "%s %s\n" "$ulx" "$uly" | gdaltransform -s_srs "$epsg" -t_srs EPSG:4326)
    read -r URlon URlat < <(printf "%s %s\n" "$urx" "$ury" | gdaltransform -s_srs "$epsg" -t_srs EPSG:4326)
    read -r LLlon LLlat < <(printf "%s %s\n" "$llx" "$lly" | gdaltransform -s_srs "$epsg" -t_srs EPSG:4326)
    read -r LRlon LRlat < <(printf "%s %s\n" "$lrx" "$lry" | gdaltransform -s_srs "$epsg" -t_srs EPSG:4326)
    W=$(printf "%s\n" "$ULlon" "$URlon" "$LLlon" "$LRlon" | awk 'NR==1{m=$1;M=$1} $1<m{m=$1} $1>M{M=$1} END{print m}')
    E=$(printf "%s\n" "$ULlon" "$URlon" "$LLlon" "$LRlon" | awk 'NR==1{m=$1;M=$1} $1<m{m=$1} $1>M{M=$1} END{print M}')
    S=$(printf "%s\n" "$ULlat" "$URlat" "$LLlat" "$LRlat" | awk 'NR==1{m=$1;M=$1} $1<m{m=$1} $1>M{M=$1} END{print m}')
    N=$(printf "%s\n" "$ULlat" "$URlat" "$LLlat" "$LRlat" | awk 'NR==1{m=$1;M=$1} $1<m{m=$1} $1>M{M=$1} END{print M}')
  fi
}

build_numeric() {
  local AOI="$1"
  local OUT="maps_v2/build/${AOI}"
  local DEM="${OUT}/${AOI}_dtm1m.tif"
  local SLOPE_NZ="${OUT}/${AOI}_slope_pct_nz.tif"
  local COST_F32="${OUT}/${AOI}_cost_f32.tif"
  local COST_COG="maps/costmaps/${AOI}_cost.tif"
  mkdir -p maps/costmaps

  # planner Float32 cost with NoData=-9999
  gdal_calc.py -A "$SLOPE_NZ" \
               -B "$OUT/${AOI}_buildings_mask.tif" \
               -C "$OUT/${AOI}_water_mask.tif" \
               -D "$OUT/${AOI}_parks_mask.tif" \
               -E "$OUT/${AOI}_roads_mask.tif" \
    --calc="where(A>-1, 2*A + 200*B + 500*C + 20*D - 80*E, -9999)" \
    --NoDataValue=-9999 --type=Float32 --overwrite \
    --co=TILED=YES --co=COMPRESS=DEFLATE --co=BIGTIFF=IF_NEEDED \
    --outfile "$COST_F32"

  # COG pack
  gdal_translate -of COG -co COMPRESS=DEFLATE -co PREDICTOR=2 "$COST_F32" "$COST_COG" || \
  gdal_translate -of GTiff -co TILED=YES -co COMPRESS=DEFLATE "$COST_F32" "$COST_COG"

  # probes: inside vs just outside (lon/lat)
  dem_bbox_wgs84 "$DEM"
  CX=$(awk -v w="$W" -v e="$E" 'BEGIN{print (w+e)/2.0}')
  CY=$(awk -v s="$S" -v n="$N" 'BEGIN{print (s+n)/2.0}')
  OX=$(awk -v w="$W" 'BEGIN{print w-0.002}') ; OY="$CY"

  echo "[$AOI] stats:" && gdalinfo "$COST_COG" -stats | egrep "Minimum=|Maximum=|Mean=|StdDev=" || true
  echo "[$AOI] sample inside ($CX,$CY):" && gdallocationinfo -wgs84 "$COST_COG" -geoloc -valonly -lon "$CX" -lat "$CY" || true
  echo "[$AOI] sample just OUTSIDE ($OX,$OY) → expect empty/NoData:" && gdallocationinfo -wgs84 "$COST_COG" -geoloc -valonly -lon "$OX" -lat "$OY" || true

  # republish MBTiles from existing color 3857 (visual only)
  local COL3857="${OUT}/${AOI}_cost_color_3857.tif"
  scripts/maps/mbtiles_from_tif.sh "$COL3857" "${AOI}_cost_color" >/dev/null || true
}

# Build BOTH AOIs (no prompts)
build_numeric rural_mo
build_numeric toronto

# serve tiles
scripts/maps/serve_mbtiles.sh || true
echo "Services: http://127.0.0.1:8001/services"
