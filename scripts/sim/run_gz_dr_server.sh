#!/usr/bin/env bash
set -euo pipefail
SEED="${SEED:-42}"
MIN_WIND_MPS="${MIN_WIND_MPS:-2}"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUTDIR="artifacts/sim/randomization/${STAMP}"
mkdir -p "$OUTDIR" artifacts/sim/tmp

python simulation/domain_randomization/scripts/apply_randomization.py \
  --seed "$SEED" --out "$OUTDIR"

test -f "$OUTDIR/last_profile.json" || \
  cp artifacts/randomization/last_profile.json "$OUTDIR/last_profile.json"

python scripts/sim/apply_dr_to_gz.py \
  --profile "$OUTDIR/last_profile.json" \
  --template simulation/domain_randomization/assets/base_airfield.sdf.tmpl \
  --min-wind-mps "$MIN_WIND_MPS" \
  --out artifacts/sim/tmp/world_dr.sdf

export GZ_SIM_RESOURCE_PATH="$(pwd)/simulation/domain_randomization/assets:${GZ_SIM_RESOURCE_PATH:-}"
echo "✅ Gazebo server starting with: artifacts/sim/tmp/world_dr.sdf"
exec gz sim -s -r artifacts/sim/tmp/world_dr.sdf
