#!/usr/bin/env bash
set -euo pipefail
AREA="${1:-toronto_downtown}"

# Synthesize a tiny DEM if missing
python3 scripts/maps/ensure_smoke_dem.py "$AREA"

# Run the same command the workflow uses
AREA="$AREA" ./scripts/maps/make_costmap.sh --yaml scripts/maps/cost_recipe.yaml
