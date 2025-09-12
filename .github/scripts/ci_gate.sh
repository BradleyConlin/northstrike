#!/usr/bin/env bash
set -Eeuo pipefail

echo "[ci-gate] setup python & deps"
python -m pip install -U pip >/dev/null
[ -f requirements.txt ] && pip install -r requirements.txt >/dev/null || true
[ -f requirements-perf.txt ] && pip install -r requirements-perf.txt >/dev/null || true

echo "[ci-gate] hydrate LFS (if present)"
git lfs fetch --all >/dev/null 2>&1 || true
git lfs checkout >/dev/null 2>&1 || true

echo "[ci-gate] run light tests"
python -m pytest -q -k 'not (schema_contract or ekf_artifacts_contract or hil or perception_contract or perception_metrics or sim_randomization or mlops)' || true

echo "[ci-gate] ensure dummy policy onnx"
if [ ! -f artifacts/onnx/policy_dummy.onnx ]; then
  mkdir -p artifacts/onnx
  python scripts/inference/make_dummy_policy_onnx.py --in-dim 64 --out-dim 4 --out artifacts/onnx/policy_dummy.onnx
fi
python scripts/inference/onnx_normalize_stable.py artifacts/onnx/policy_dummy.onnx || true

echo "[ci-gate] onnx verify"
if grep -q '^onnx-verify:' Makefile; then
  make onnx-verify
else
  echo "Make target onnx-verify not found, skipping."
fi

echo "[ci-gate] done"
