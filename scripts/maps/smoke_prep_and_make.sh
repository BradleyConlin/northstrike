#!/usr/bin/env bash
set -euo pipefail
AREA="${1:-toronto_downtown}"
python3 scripts/maps/ensure_smoke_dem.py "$AREA"
AREA="$AREA" ./scripts/maps/make_costmap.sh --yaml scripts/maps/cost_recipe.yaml
