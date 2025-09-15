#!/usr/bin/env bash
set -euo pipefail
PX4_DIR="${PX4_DIR:?Set PX4_DIR to your PX4-Autopilot path}"
MODEL="${MODEL:-gz_x500}"
cd "$PX4_DIR"
# PX4 waits for Gazebo server; run headless to skip the GUI
PX4_GZ_STANDALONE=1 HEADLESS=1 make px4_sitl "$MODEL"
