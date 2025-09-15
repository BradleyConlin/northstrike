## Visual Domain Randomization (wind/sun/scene/PBR)

Render a DR world and launch SITL:

```bash
# optional: tweak via env
SEED=123 MIN_WIND_MPS=2 LAUNCH_QGC=1 \
  scripts/sim/ns_sitl_dr.sh
