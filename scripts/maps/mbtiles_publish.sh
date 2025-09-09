#!/usr/bin/env bash
set -euo pipefail

# MBTiles publisher: builds gray (from Float32 cost) + color (from RGBA) as MBTiles.
# Usage:
#   bash scripts/maps/mbtiles_publish.sh
#   AREA=toronto_downtown bash scripts/maps/mbtiles_publish.sh
#   bash scripts/maps/mbtiles_publish.sh toronto_downtown
#
# Outputs: artifacts/maps/mbtiles/<AREA>_cost_{gray,color}.mbtiles

need_bin() { command -v "$1" >/dev/null 2>&1 || { echo "ERROR: '$1' not found"; exit 2; }; }

main() {
  need_bin gdal_translate; need_bin gdaladdo; need_bin gdalinfo
  cd "$(git rev-parse --show-toplevel)"
  mkdir -p artifacts/maps/mbtiles

  # Accept AREA from env or first positional arg
  if [[ -z "${AREA:-}" && -n "${1-}" ]]; then AREA="$1"; fi

  local areas=()
  if [[ -n "${AREA:-}" ]]; then
    areas+=("$AREA")
  else
    while IFS= read -r -d '' f; do
      areas+=("$(basename "$f" | sed 's/_cost\.tif$//')")
    done < <(find maps/costmaps -maxdepth 1 -type f -name '*_cost.tif' -print0 2>/dev/null || true)
  fi

  [[ ${#areas[@]} -gt 0 ]] || { echo "No maps/costmaps/*_cost.tif found"; exit 1; }

  for area in "${areas[@]}"; do
    local float_src="maps/costmaps/${area}_cost.tif"
    local rgba_src="maps/costmaps/${area}_cost_rgba.tif"
    [[ -f "$float_src" ]] || { echo "WARN: $float_src missing; skip $area"; continue; }

    # Gray MBTiles from Float32 cost (scale 0→1500 → 1→255)
    local out_gray="artifacts/maps/mbtiles/${area}_cost_gray.mbtiles"
    echo "==> GRAY MBTiles: $area"
    gdal_translate -q -of MBTILES -ot Byte -scale 0 1500 1 255 -co TILE_FORMAT=PNG -co QUALITY=100 "$float_src" "$out_gray"
    gdaladdo -q -r average "$out_gray" 2 4 8 16 32 || true

    # Optional color MBTiles from RGBA
    local outputs=("$out_gray")
    if [[ -f "$rgba_src" ]]; then
      local out_color="artifacts/maps/mbtiles/${area}_cost_color.mbtiles"
      echo "==> COLOR MBTiles: $area"
      gdal_translate -q -of MBTILES -co TILE_FORMAT=PNG -co QUALITY=100 "$rgba_src" "$out_color"
      gdaladdo -q -r nearest "$out_color" 2 4 8 16 32 || true
      outputs+=("$out_color")
    else
      echo "WARN: $rgba_src not found; skipping COLOR MBTiles for $area"
    fi

    # Quick metadata peek (only over existing outputs)
    for f in "${outputs[@]}"; do
      echo "--- $f ---"
      gdalinfo "$f" | sed -n '1,25p'
    done
  done

  echo "Done → artifacts/maps/mbtiles/"
}

main "$@"
