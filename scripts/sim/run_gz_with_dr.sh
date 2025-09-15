#!/usr/bin/env bash
set -euo pipefail

SEED="${SEED:-42}"
MIN_WIND_MPS="${MIN_WIND_MPS:-2}"
WORLD_PATH="artifacts/sim/tmp/world_dr.sdf"

# Generate DR profile + SDF world (reuses your target)
make -s sim-rand-world SEED="$SEED" MIN_WIND_MPS="$MIN_WIND_MPS"

# Launch Gazebo Sim if available
if ! command -v gz >/dev/null 2>&1; then
  echo "gz not found; install Gazebo Sim or run inside your sim container." >&2
  echo "World prepared at: $WORLD_PATH"
  exit 0
fi

echo "Launching Gazebo Sim with world: $WORLD_PATH"
exec gz sim -r "$WORLD_PATH"
