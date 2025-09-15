#!/usr/bin/env bash
# ns_px4_bootstrap.sh
# One-stop PX4 SITL setup/launch for Gazebo Harmonic (v1.16.0).
# Usage:
#   scripts/sim/ns_px4_bootstrap.sh                # setup + build + launch gz_x500
#   scripts/sim/ns_px4_bootstrap.sh --qgc          # also launches QGC AppImage if present
#   PX4_DIR=/custom/path scripts/sim/ns_px4_bootstrap.sh
#
set -euo pipefail

PX4_DIR="${PX4_DIR:-$HOME/dev/PX4-Autopilot}"
PX4_TAG="${PX4_TAG:-v1.16.0}"   # Harmonic LTS supported by PX4
LAUNCH_QGC=0
QGC_APP="${QGC_APP:-$HOME/Downloads/QGroundControl-x86_64.AppImage}"

for arg in "$@"; do
  case "$arg" in
    --qgc) LAUNCH_QGC=1 ;;
    *) echo "Unknown arg: $arg" >&2; exit 2 ;;
  esac
done

echo "➡️  PX4 dir: $PX4_DIR"
echo "➡️  PX4 tag: $PX4_TAG"

if ! command -v git >/dev/null; then
  echo "git not found. Install git first." >&2
  exit 1
fi

# Clone if missing
if [ ! -d "$PX4_DIR/.git" ]; then
  echo "⎇  Cloning PX4-Autopilot → $PX4_DIR"
  git clone https://github.com/PX4/PX4-Autopilot.git "$PX4_DIR"
fi

cd "$PX4_DIR"
echo "⎇  Fetching tags..."
git fetch --tags

# Make sure we can switch cleanly: drop untracked sim assets that often block checkout
if [ -d Tools/simulation/gz ]; then
  echo "🧹 Cleaning untracked files under Tools/simulation/gz"
  git clean -fd Tools/simulation/gz || true
fi

echo "📌 Checking out $PX4_TAG"
git checkout "$PX4_TAG"

echo "🔁 Submodules…"
git submodule update --init --recursive

# Build Harmonic target
echo "🛠️  Building px4_sitl gz_x500 (Gazebo Harmonic)"
make clean || true
make px4_sitl gz_x500

# Optionally launch QGC (AppImage)
if [ "$LAUNCH_QGC" -eq 1 ]; then
  if [ -x "$QGC_APP" ]; then
    echo "🛰️  Launching QGroundControl"
    (QT_QPA_PLATFORM=xcb QT_OPENGL=desktop "$QGC_APP" --clear-settings >/dev/null 2>&1 &)
  else
    echo "⚠️  QGC AppImage not found at $QGC_APP (skipping)."
  fi
fi

echo "🚀 Starting PX4 SITL + Gazebo Harmonic (x500, default world)"
# PX4 docs: run Gazebo Harmonic with gz-targets like gz_x500
# https://docs.px4.io/main/en/sim_gazebo_gz/
PX4_GZ_MODEL=x500 PX4_GZ_WORLD=forest make px4_sitl gz_x500
