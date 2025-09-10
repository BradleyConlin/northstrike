#!/usr/bin/env bash
# Canada-only numerics: builds planner Float32 cost COGs and prints stats/samples.
# AOIs default to: toronto ottawa. Override with:
#   ONLY_AOI=toronto bash scripts/maps/finish_step5_numeric.sh
# or:
#   AOIS="toronto ottawa" bash scripts/maps/finish_step5_numeric.sh
set -euo pipefail

# ---------- helpers ----------
dem_bbox_wgs84() {
  # Fills W,S,E,N (floats, lon/lat) for the given DEM
  local dem="$1"
  if gdalinfo -json "$dem" | jq -e '.wgs84Extent' >/dev/null 2>&1; then
    read -r W S E N < <(gdalinfo -json "$dem" | jq -r '
      .wgs84Extent.coordinates[0] as $p
      | [ ($p|map(.[0])|min),
          ($p|map(.[1])|min),
          ($p|map(.[0])|max),
          ($p|map(.[1])|max) ] | @tsv')
  else
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

seed_zero_mask() {
  # Creates a writable Byte 0/1 mask aligned to DEM (all zeros). No NoData.
  local dem="$1" out="$2"
  local w h geotrans srs
  read -r w h < <(gdalinfo -json "$dem" | jq -r '.size|@tsv')
  geotrans=$(gdalinfo -json "$dem" | jq -r '.geoTransform|@csv')
  srs=$(gdalsrsinfo -o wkt "$dem")
  gdal_translate -ot Byte -of GTiff -co TILED=YES -co COMPRESS=DEFLATE /vsimem/empty "$out" \
    -outsize "$w" "$h" -a_ullr $(gdalinfo -json "$dem" | jq -r '.cornerCoordinates.upperLeft+" "+.cornerCoordinates.lowerRight' | tr -d '[],') \
    -a_srs "$srs" >/dev/null 2>&1 || true
  gdal_edit.py -unsetnodata "$out" || true
  # Fill with 0 explicitly
  gdal_calc.py -A "$out" --calc="0*A" --NoDataValue=None --type=Byte --overwrite --outfile "$out" >/dev/null 2>&1 || true
}

build_numeric() {
  local AOI="$1"
  local OUT="maps_v2/build/${AOI}"
  local DEM="${OUT}/${AOI}_dtm1m.tif"
  local SLOPE="${OUT}/${AOI}_slope_pct.tif"
  local SLOPE_NZ="${OUT}/${AOI}_slope_pct_nz.tif"
  local COST_F32="${OUT}/${AOI}_cost_f32.tif"
  local COST_COG="maps/costmaps/${AOI}_cost.tif"
  mkdir -p "$OUT" maps/costmaps

  if [[ ! -f "$DEM" ]]; then
    echo "[skip:$AOI] DEM missing at $DEM"
    return 0
  fi

  # Ensure masks exist (if MBTiles step wasn’t run yet). Keep masks strict 0/1.
  for m in buildings water parks roads; do
    [[ -f "$OUT/${AOI}_${m}_mask.tif" ]] || seed_zero_mask "$DEM" "$OUT/${AOI}_${m}_mask.tif"
    gdal_edit.py -unsetnodata "$OUT/${AOI}_${m}_mask.tif" >/dev/null 2>&1 || true
  done

  # Ensure slope% exists and clamp to non-negative for numerics.
  if [[ ! -f "$SLOPE" ]]; then
    gdaldem slope -p "$DEM" "$SLOPE" >/dev/null 2>&1 || gdaldem slope "$DEM" "$SLOPE"
    # -p => percent slope; falls back to degrees if -p unsupported (older builds). Docs: percent option exists.
  fi
  gdal_calc.py -A "$SLOPE" --calc="(A>=0)*A" --type=Float32 --overwrite \
    --co=TILED=YES --co=COMPRESS=DEFLATE --outfile "$SLOPE_NZ"

  # Planner Float32 cost with NoData=-9999 (numerical truth raster)
  gdal_calc.py -A "$SLOPE_NZ" \
               -B "$OUT/${AOI}_buildings_mask.tif" \
               -C "$OUT/${AOI}_water_mask.tif" \
               -D "$OUT/${AOI}_parks_mask.tif" \
               -E "$OUT/${AOI}_roads_mask.tif" \
    --calc="where(A>-1, 2*A + 200*B + 500*C + 20*D - 80*E, -9999)" \
    --NoDataValue=-9999 --type=Float32 --overwrite \
    --co=TILED=YES --co=COMPRESS=DEFLATE --co=BIGTIFF=IF_NEEDED \
    --outfile "$COST_F32"

  # COG pack (prefer COG, fallback to GTiff)
  gdal_translate -of COG -co COMPRESS=DEFLATE -co PREDICTOR=2 "$COST_F32" "$COST_COG" || \
  gdal_translate -of GTiff -co TILED=YES -co COMPRESS=DEFLATE "$COST_F32" "$COST_COG"

  # Probe inside/outside using W,S,E,N from DEM
  dem_bbox_wgs84 "$DEM"
  CX=$(awk -v w="$W" -v e="$E" 'BEGIN{print (w+e)/2.0}')
  CY=$(awk -v s="$S" -v n="$N" 'BEGIN{print (s+n)/2.0}')
  OX=$(awk -v w="$W" 'BEGIN{print w-0.002}') ; OY="$CY"

  echo "[$AOI] stats:" && gdalinfo "$COST_COG" -stats | egrep "Minimum=|Maximum=|Mean=|StdDev=" || true
  echo "[$AOI] sample inside ($CX,$CY):" && gdallocationinfo -wgs84 "$COST_COG" -geoloc -valonly -lon "$CX" -lat "$CY" || true
  echo "[$AOI] sample just OUTSIDE ($OX,$OY) → expect empty/NoData:" && gdallocationinfo -wgs84 "$COST_COG" -geoloc -valonly -lon "$OX" -lat "$OY" || true
}

# ---------- entrypoint ----------
ONLY_AOI="${ONLY_AOI:-}"
if [[ -n "${ONLY_AOI}" ]]; then
  AOIS=("$ONLY_AOI")
else
  # Canada-only default set
  AOIS=(toronto ottawa)
fi

for aoi in "${AOIS[@]}"; do
  build_numeric "$aoi"
done

# (Optional) keep mbtiles server up-to-date (no-op if not present)
scripts/maps/serve_mbtiles.sh >/dev/null 2>&1 || true
echo "Services (if server running): http://127.0.0.1:8001/services"
