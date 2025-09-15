# Northstrike SITL DR Launcher — Quick Start

## Requirements
- Ubuntu 22.04+, PX4 v1.16, Gazebo Harmonic.
- QGroundControl AppImage with deps: libfuse2 + GStreamer (video). See docs.
- QGC listens on UDP 14550; PX4 SITL streams there by default.

## One-liners
Launch QGC (clean profile):
QT_QPA_PLATFORM=xcb QT_OPENGL=desktop ~/Downloads/QGroundControl.AppImage --clear-settings &

Build DR world + start Gazebo + attach PX4:
SEED=123 MIN_WIND_MPS=2 LAUNCH_QGC=1 scripts/sim/ns_px4_bootstrap.sh

## What “Ready” looks like
- QGC shows the vehicle connected and **Ready**.
- PX4 console prints: “Gazebo world is ready” then “Ready for takeoff!”.

## Troubleshooting
- **No models/world assets**: ensure GZ_SIM_RESOURCE_PATH is exported (launcher does this).
- **QGC doesn’t see the vehicle**: confirm it’s listening on UDP 14550; PX4 sends MAVLink there.
- **Slow EKF settle (sim only)**: temporarily set `EKF2_MAG_TYPE=1`, `EKF2_GPS_CHECK=0`, then `param save`.

## Acceptance (fast)
- Run `make sim-acceptance` (headless smoke): starts launcher briefly, looks for startup lines, then exits.
- Logs: `artifacts/sim/acceptance_smoke.log`.
