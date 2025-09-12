#!/usr/bin/env bash
set -euo pipefail

OUT_DIR="artifacts/doctor"
mkdir -p "$OUT_DIR"
OUT="$OUT_DIR/open_sweep_$(date +%Y%m%d_%H%M%S).txt"

section() { echo -e "\n====== $1 ======\n" | tee -a "$OUT"; }

section "Env info"
( python -V; pip --version; pip check || true ) 2>&1 | tee -a "$OUT"

section "Repo Doctor"
( python scripts/dev/repo_doctor.py ) 2>&1 | tee -a "$OUT" || true

section "Git status"
git status -sb 2>&1 | tee -a "$OUT"

section "Unpushed commits"
git log --branches --not --remotes --oneline 2>&1 | tee -a "$OUT" || true

section "Stashes"
git stash list 2>&1 | tee -a "$OUT" || true

section "Branches not merged into origin/main"
git fetch --prune 2>&1 | tee -a "$OUT"
git branch -vv --no-merged origin/main 2>&1 | tee -a "$OUT" || true
section "Remote branches not merged into origin/main"
git branch -r --no-merged origin/main 2>&1 | tee -a "$OUT" || true

section "Open PRs"
( gh pr status && gh pr list --state open --limit 20 ) 2>&1 | tee -a "$OUT" || true

section "Open Issues"
gh issue list --state open --limit 20 2>&1 | tee -a "$OUT" || true

section "Recent CI runs"
gh run list --limit 10 2>&1 | tee -a "$OUT" || true

section "Pre-commit (all files)"
pre-commit run --all-files 2>&1 | tee -a "$OUT" || true

section "Git LFS status"
git lfs status 2>&1 | tee -a "$OUT" || true

section "Large files on disk (untracked or ignored)"
find . -type f -size +50M -not -path "./.git/*" -not -path "./.venv/*" 2>/dev/null \
  | sed 's/^/  /' | tee -a "$OUT" || true

section "TODO / FIXME / HACK / XXX"
if command -v rg >/dev/null; then
  rg -n --no-heading -S "TODO|FIXME|HACK|XXX" \
    -g '!{.git,.venv,artifacts,mlruns,dist,build,node_modules,**/*.onnx,**/*.tif,**/*.mbtiles}' \
    2>/dev/null | tee -a "$OUT" || true
else
  grep -RInE "TODO|FIXME|HACK|XXX" \
    --exclude-dir={.git,.venv,artifacts,mlruns,dist,build,node_modules} \
    --exclude='*.onnx' --exclude='*.tif' --exclude='*.mbtiles' . \
    2>/dev/null | tee -a "$OUT" || true
fi

if [[ "${RUN_SMOKE:-0}" == "1" && $(command -v pytest) ]]; then
  section "Smoke tests"
  pytest -q \
    training/tests/sim_randomization/test_randomization.py::test_values_within_bounds \
    training/tests/training/test_training_pipeline.py::test_outputs_exist_and_nonempty \
    training/tests/mlops/test_mlflow_tracking.py \
    training/tests/mlops/test_registry_smoke.py \
    training/tests/inference/test_depth_offline_smoke.py \
    training/tests/inference/test_policy_offline_smoke.py \
    training/tests/inference/test_e2e_tick_smoke.py \
    training/tests/sysid/test_sysid_estimator.py \
    2>&1 | tee -a "$OUT" || true
fi

section "Packaging (dry-run discovery)"
python - <<'PY' 2>&1 | tee -a "$OUT" || true
from setuptools import find_packages
pkgs = find_packages(exclude=[
  ".venv","tests","artifacts","mlruns","dist","build",
  "maps","maps_v2","maps*","viewer","deploy","datasets",
  "sim","simulation","configs","tiles","constraints"
])
print("discoverable packages:", pkgs)
print("NOTE: repo uses a flat layout; consider src/ layout or explicit `packages=`.")
PY

echo -e "\nReport written to: $OUT" | tee -a "$OUT"
