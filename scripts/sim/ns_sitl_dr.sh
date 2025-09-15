#!/usr/bin/env bash
set -euo pipefail

NS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
SEED="${SEED:-123}"
MIN_WIND_MPS="${MIN_WIND_MPS:-2}"
WORLD_NAME="northstrike_airfield"

# 1) Build DR world
make -C "$NS_ROOT" sim-rand-world SEED="$SEED" MIN_WIND_MPS="$MIN_WIND_MPS"

# 2) Stage world under a Gazebo resource path with the expected name
mkdir -p "$HOME/.simulation-gazebo/worlds"
ln -sf "$NS_ROOT/artifacts/sim/tmp/world_dr.sdf" \
       "$HOME/.simulation-gazebo/worlds/${WORLD_NAME}.sdf"

# 3) Ensure Gazebo can find it; kill any stale gz servers
export GZ_SIM_RESOURCE_PATH="$HOME/.simulation-gazebo/worlds:${GZ_SIM_RESOURCE_PATH:-}"
pkill -9 -f 'gz(sim|server|client)' >/dev/null 2>&1 || true

# 4) Launch PX4 (regular mode: PX4 starts Gazebo)
cd "$HOME/dev/PX4-Autopilot"
PX4_GZ_WORLD="$WORLD_NAME" make px4_sitl gz_x500
