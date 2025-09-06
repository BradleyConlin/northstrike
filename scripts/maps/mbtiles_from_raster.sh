#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   scripts/maps/mbtiles_from_raster.sh <input_rgba_tif> <out_mbtiles>
# Example:
#   scripts/maps/mbtiles_from_raster.sh maps/costmaps/yyz_downtown_cost_rgba.tif maps/mbtiles/yyz_downtown_cost.mbtiles

in_tif="${1:-}"; out_mb="${2:-}"
if [[ -z "${in_tif}" || -z "${out_mb}" ]]; then
  echo "Usage: $0 <input_rgba_tif> <out_mbtiles>" >&2; exit 2
fi

mkdir -p "$(dirname "$out_mb")"

# Create MBTiles (WebMercator). gdal_translate auto-detects and writes metadata.
gdal_translate -of MBTILES "$in_tif" "$out_mb"

# Build overviews (zooms). Average for continuous rasters; nearest for masks.
# We detect mask vs cost by filename; override with MBTILES_RESAMPLING if needed.
resamp="AVERAGE"
case "$out_mb" in
  *mask*.mbtiles) resamp="NEAREST" ;;
esac
gdaladdo -r "$resamp" "$out_mb" 2 4 8 16 32
echo "Wrote $out_mb"
