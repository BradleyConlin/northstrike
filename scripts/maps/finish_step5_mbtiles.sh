#!/usr/bin/env bash
# Canada-only MBTiles builder: computes slope, builds OSM masks, colorizes, warps to EPSG:3857, publishes MBTiles.
# Usage:
#   bash scripts/maps/finish_step5_mbtiles.sh                # builds default AOIs (toronto ottawa)
#   ONLY_AOI=toronto bash scripts/maps/finish_step5_mbtiles.sh
#   AOIS="toronto ottawa" bash scripts/maps/finish_step5_mbtiles.sh
set -euo pipefail

serve="scripts/maps/serve_mbtiles.sh"
mbtiles="scripts/maps/mbtiles_from_tif.sh"
ramp="scripts/maps/ramps/cost_ramp_v2.txt"
masks="maps_v2/bin/osm_masks_from_pbf.sh"

bbox_from_dem() {
  # Fills W,S,E,N for DEM in lon/lat
  local dem="$1"
  if gdalinfo -json "$dem" | jq -e '.wgs84Extent' >/dev/null; then
    read -r W S E N < <(gdalinfo -json "$dem" | jq -r '
      .wgs84Extent.coordinates[0] as $p |
      "\([ $p[] | .[0] ] | min) \([ $p[] | .[1] ] | min) \([ $p[] | .[0] ] | max) \([ $p[] | .[1] ] | max)"')
  else
    local epsg ulx uly lrx lry
    epsg=$(gdalsrsinfo -o epsg "$dem" | sed -n 's/.*\(EPSG:[0-9]\+\).*/\1/p' | head -n1)
    read -r ulx uly < <(gdalinfo -json "$dem" | jq -r '.cornerCoordinates.upperLeft | @tsv')
    read -r lrx lry < <(gdalinfo -json "$dem" | jq -r '.cornerCoordinates.lowerRight | @tsv')
    read -r W S < <(printf "%s %s\n" "$ulx" "$lry" | gdaltransform -s_srs "$epsg" -t_srs EPSG:4326 | awk '{print $1, $2}')
    read -r E N < <(printf "%s %s\n" "$lrx" "$uly" | gdaltransform -s_srs "$epsg" -t_srs EPSG:4326 | awk '{print $1, $2}')
  fi
}

build_one() {
  local AOI="$1"

  local OUT="maps_v2/build/${AOI}"
  local DEM="${OUT}/${AOI}_dtm1m.tif"
  mkdir -p "$OUT"

  if [[ ! -f "$DEM" ]]; then
    echo "[skip:$AOI] DEM missing at $DEM"
    return 0
  fi

  # AOI → which regional OSM PBF to start from (Canada-only for now)
  local REGIONAL BBOX
  case "$AOI" in
    toronto|ottawa)
      REGIONAL="artifacts/maps/osm/ontario-latest.osm.pbf"
      ;;
    *)
      echo "[skip:$AOI] Not in Canada-only set (toronto|ottawa)."
      return 0
      ;;
  esac
  BBOX="artifacts/maps/osm/${AOI}_bbox.osm.pbf"

  # Get exact lon/lat bbox from the DEM and clip the regional PBF
  bbox_from_dem "$DEM"   # sets W,S,E,N
  # osmium expects bbox in LEFT,BOTTOM,RIGHT,TOP (lon/lat).
  osmium extract -O -b "$W,$S,$E,$N" "$REGIONAL" -o "$BBOX"

  # Create slope% if absent (percent with -p; nodata handled by tool).
  if [[ ! -f "$OUT/${AOI}_slope_pct.tif" ]]; then
    gdaldem slope -p "$DEM" "$OUT/${AOI}_slope_pct.tif" >/dev/null 2>&1 || gdaldem slope "$DEM" "$OUT/${AOI}_slope_pct.tif"
    # -p => percent slope (official option); falls back to degrees if needed.
  fi

  # Clean old masks (ensure writable fresh masks)
  rm -f "$OUT/${AOI}"_*_mask.tif

  # Build roads/water/parks/buildings masks aligned to DEM grid
  "$masks" "$AOI" "$BBOX" "$DEM"

  # Normalize inputs used for viz cost (clear NoData so color always renders)
  gdal_edit.py -unsetnodata "$OUT/${AOI}_slope_pct.tif" || true
  for m in roads water parks buildings; do
    gdal_edit.py -unsetnodata "$OUT/${AOI}_${m}_mask.tif" || true
  done

  # Non-negative slope (remove tiny negatives from edges)
  gdal_calc.py -A "$OUT/${AOI}_slope_pct.tif" \
    --calc="(A>=0)*A" --type=Float32 --overwrite \
    --co=TILED=YES --co=COMPRESS=DEFLATE \
    --outfile "$OUT/${AOI}_slope_pct_nz.tif"

  # Viz-only cost (clamped non-negative, no NoData)
  gdal_calc.py -A "$OUT/${AOI}_slope_pct_nz.tif" \
               -B "$OUT/${AOI}_buildings_mask.tif" \
               -C "$OUT/${AOI}_water_mask.tif" \
               -D "$OUT/${AOI}_parks_mask.tif" \
               -E "$OUT/${AOI}_roads_mask.tif" \
    --calc="maximum(0, 2*A + 200*B + 500*C + 20*D - 80*E)" \
    --type=Float32 --overwrite \
    --co=TILED=YES --co=COMPRESS=DEFLATE --co=BIGTIFF=IF_NEEDED \
    --outfile "$OUT/${AOI}_cost_clamp0.tif"

  # Colorize (UTM), then warp to Web Mercator (EPSG:3857), then publish MBTiles
  gdaldem color-relief -alpha "$OUT/${AOI}_cost_clamp0.tif" "$ramp" \
    "$OUT/${AOI}_cost_color_utm.tif"
  gdalwarp -t_srs EPSG:3857 -r near -dstalpha \
    "$OUT/${AOI}_cost_color_utm.tif" "$OUT/${AOI}_cost_color_3857.tif"

  "$mbtiles" "$OUT/${AOI}_cost_color_3857.tif" "${AOI}_cost_color"
}

main() {
  ONLY_AOI="${ONLY_AOI:-}"
  if [[ -n "${ONLY_AOI}" ]]; then
    AOIS=("$ONLY_AOI")
  else
    AOIS=(toronto ottawa)  # default Canada-only
  fi

  for a in "${AOIS[@]}"; do
    build_one "$a"
  done

  # (Re)start local mbtiles server & show links
  "$serve" || true
  echo "Services: http://127.0.0.1:8001/services"
  for a in "${AOIS[@]}"; do
    echo "Open viewer:  http://127.0.0.1:8000/viewer/mbtiles_overlay.html?svc=${a}_cost_color"
  done
}

main "$@"
