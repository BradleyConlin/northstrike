#!/usr/bin/env bash
set -euo pipefail

# Usage:
#   SEED=123 MIN_WIND_MPS=2 LAUNCH_QGC=1 scripts/sim/ns_sitl_dr.sh
#
# Renders a DR’d world from configs/sim/randomization/visual_profile.json, then launches Gazebo+PX4.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$REPO_ROOT"

PROFILE="${PROFILE:-configs/sim/randomization/visual_profile.json}"
TEMPLATE="simulation/domain_randomization/assets/base_airfield.sdf.tmpl"
OUT_DIR="artifacts/sim/tmp"
SDF_OUT="${OUT_DIR}/world_dr.sdf"

SEED="${SEED:-123}"
MIN_WIND_MPS="${MIN_WIND_MPS:-2}"
LAUNCH_QGC="${LAUNCH_QGC:-0}"

mkdir -p "$OUT_DIR"

echo "🎨 Rendering DR world → ${SDF_OUT}"
python scripts/sim/apply_dr_to_gz.py \
  --profile "$PROFILE" \
  --template "$TEMPLATE" \
  --out "$SDF_OUT" \
  --min-wind-mps "$MIN_WIND_MPS"

# Basic assertions (wind + PBR present)
grep -q '<wind>' "$SDF_OUT" || { echo "✖ wind block missing"; exit 1; }
grep -q '<pbr>'  "$SDF_OUT" || { echo "✖ PBR missing"; exit 1; }
echo "✅ world rendered with <wind> and <pbr>"

# Parse <world name="...">
WORLD_NAME="$(awk -F\" '/<world[[:space:]]+name=/{print $2; exit}' "$SDF_OUT")"
WORLD_NAME="${WORLD_NAME:-northstrike_airfield}"
echo "🌍 World name: ${WORLD_NAME}"

# Ensure Gazebo can find our assets & the rendered SDF directory
ASSETS_DIR="${REPO_ROOT}/simulation/domain_randomization/assets"
export GZ_SIM_RESOURCE_PATH="${ASSETS_DIR}:${OUT_DIR}:${GZ_SIM_RESOURCE_PATH:-}"
echo "🔎 GZ_SIM_RESOURCE_PATH=${GZ_SIM_RESOURCE_PATH}"

# Hand off to the PX4 bootstrap (it clones/builds as needed and launches the sim)
# We set PX4_GZ_WORLD to the parsed world name and stick with the x500 model.
PX4_SIM_MODEL="${PX4_SIM_MODEL:-x500}" \
PX4_GZ_WORLD="${WORLD_NAME}" \
SEED="${SEED}" MIN_WIND_MPS="${MIN_WIND_MPS}" LAUNCH_QGC="${LAUNCH_QGC}" \
scripts/sim/ns_px4_bootstrap.sh
