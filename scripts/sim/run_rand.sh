#!/usr/bin/env bash
set -Eeuo pipefail

CONFIG="${CONFIG:-configs/sim/randomization/default.yaml}"
SEED="${SEED:-$RANDOM$RANDOM}"
STAMP="$(date +%Y%m%d_%H%M%S)"
OUTDIR="artifacts/sim/randomization/${STAMP}"
SIM_LAUNCH="${SIM_LAUNCH:-scripts/start_simulation.py}"  # can override per env

mkdir -p "$OUTDIR"

# 1) Apply randomization (always passes explicit flags)
python simulation/domain_randomization/scripts/apply_randomization.py \
  --profile "$CONFIG" \
  --out "$OUTDIR" \
  --samples 1 \
  --seed "$SEED" \
  --jsonl "$OUTDIR/rand.jsonl" 2>&1 | tee "$OUTDIR/apply_randomization.log"

# 2) Try to launch sim if launcher exists; otherwise skip gracefully
if [ -f "$SIM_LAUNCH" ]; then
  python "$SIM_LAUNCH" "$@" 2>&1 | tee "$OUTDIR/sim.log"
else
  echo "[run_rand] No sim launcher at '$SIM_LAUNCH'. Skipping sim step."
fi
