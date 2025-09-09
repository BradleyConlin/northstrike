#!/usr/bin/env bash
set -euo pipefail

# Build both AOIs unless ONLY_AOI is set to "toronto" or "rural_mo".
ONLY_AOI="${ONLY_AOI:-}"

serve="scripts/maps/serve_mbtiles.sh"
mbtiles="scripts/maps/mbtiles_from_tif.sh"
ramp="scripts/maps/ramps/cost_ramp_v2.txt"
masks="maps_v2/bin/osm_masks_from_pbf.sh"

bbox_from_dem() {
  local dem="$1"
  if gdalinfo -json "$dem" | jq -e '.wgs84Extent' >/dev/null; then
    read W S E N < <(gdalinfo -json "$dem" | jq -r '
      .wgs84Extent.coordinates[0] as $p |
      "\([ $p[] | .[0] ] | min) \([ $p[] | .[1] ] | min) \([ $p[] | .[0] ] | max) \([ $p[] | .[1] ] | max)"')
  else
    local epsg ulx uly lrx lry
    epsg=$(gdalsrsinfo -o epsg "$dem" | sed -n 's/.*\(EPSG:[0-9]\+\).*/\1/p' | head -n1)
    read ulx uly < <(gdalinfo -json "$dem" | jq -r '.cornerCoordinates.upperLeft | @tsv')
    read lrx lry < <(gdalinfo -json "$dem" | jq -r '.cornerCoordinates.lowerRight | @tsv')
    read W S < <(printf "%s %s\n" "$ulx" "$lry" | gdaltransform -s_srs "$epsg" -t_srs EPSG:4326 | awk '{print $1, $2}')
    read E N < <(printf "%s %s\n" "$lrx" "$uly" | gdaltransform -s_srs "$epsg" -t_srs EPSG:4326 | awk '{print $1, $2}')
  fi
}

build_one() {
  local AOI="$1"

  # IMPORTANT: assign OUT first, then use it (avoids set -u 'unbound variable').
  local OUT
  OUT="maps_v2/build/${AOI}"
  local DEM
  DEM="${OUT}/${AOI}_dtm1m.tif"
  mkdir -p "$OUT"

  bbox_from_dem "$DEM"             # sets W,S,E,N in lon/lat
  local REGIONAL BBOX
  if [[ "$AOI" == "toronto" ]]; then
    REGIONAL="artifacts/maps/osm/ontario-latest.osm.pbf"
    BBOX="artifacts/maps/osm/toronto_bbox.osm.pbf"
  else
    REGIONAL="artifacts/maps/osm/missouri-latest.osm.pbf"
    BBOX="artifacts/maps/osm/rural_mo_bbox.osm.pbf"
  fi

  # Exact reclip of OSM to DEM bounds (lon,lat order)
  osmium extract -O -b "$W,$S,$E,$N" "$REGIONAL" -o "$BBOX"

  # Start clean masks to avoid read-only issues
  rm -f "$OUT/${AOI}"_*_mask.tif

  # Build roads/water/parks/buildings masks aligned to the DEM grid
  "$masks" "$AOI" "$BBOX" "$DEM"

  # Clear NoData on inputs used for viz cost
  gdal_edit.py -unsetnodata "$OUT/${AOI}_slope_pct.tif" || true
  for m in roads water parks buildings; do
    gdal_edit.py -unsetnodata "$OUT/${AOI}_${m}_mask.tif" || true
  done

  # Non-negative slope to kill seam/edge negatives
  gdal_calc.py -A "$OUT/${AOI}_slope_pct.tif" \
    --calc="(A>=0)*A" --type=Float32 --overwrite \
    --co=TILED=YES --co=COMPRESS=DEFLATE \
    --outfile "$OUT/${AOI}_slope_pct_nz.tif"

  # Viz-only cost (no NoData so colors always render)
  gdal_calc.py -A "$OUT/${AOI}_slope_pct_nz.tif" \
               -B "$OUT/${AOI}_buildings_mask.tif" \
               -C "$OUT/${AOI}_water_mask.tif" \
               -D "$OUT/${AOI}_parks_mask.tif" \
               -E "$OUT/${AOI}_roads_mask.tif" \
    --calc="maximum(0, 2*A + 200*B + 500*C + 20*D - 80*E)" \
    --type=Float32 --overwrite \
    --co=TILED=YES --co=COMPRESS=DEFLATE --co=BIGTIFF=IF_NEEDED \
    --outfile "$OUT/${AOI}_cost_clamp0.tif"

  # Colorize, warp to Web Mercator, publish MBTiles
  gdaldem color-relief -alpha "$OUT/${AOI}_cost_clamp0.tif" "$ramp" \
    "$OUT/${AOI}_cost_color_utm.tif"
  gdalwarp -t_srs EPSG:3857 -r near -dstalpha \
    "$OUT/${AOI}_cost_color_utm.tif" "$OUT/${AOI}_cost_color_3857.tif"
  "$mbtiles" "$OUT/${AOI}_cost_color_3857.tif" "${AOI}_cost_color"
}

main() {
  if [[ -n "${ONLY_AOI}" ]]; then
    echo "Building ONLY_AOI=${ONLY_AOI}"
    build_one "$ONLY_AOI"
  else
    build_one "toronto"
    build_one "rural_mo"
  fi

  # (Re)start local mbtiles server & show links
  "$serve" || true
  echo "Services: http://127.0.0.1:8001/services"
  echo "Open viewer:"
  echo "  http://127.0.0.1:8000/viewer/mbtiles_overlay.html?svc=toronto_cost_color"
  echo "  http://127.0.0.1:8000/viewer/mbtiles_overlay.html?svc=rural_mo_cost_color"
}

main "$@"
