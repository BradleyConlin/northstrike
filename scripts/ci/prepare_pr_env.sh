#!/usr/bin/env bash
set -Eeuo pipefail

echo "[ns-ci] Python & deps"
python -V || true
python - <<'PY'
import sys; print("site:", sys.path[0])
PY
python -m pip install -U pip wheel
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
else
  # fallback to the minimum we know CI needs
  pip install pyyaml onnx onnxruntime
fi

echo "[ns-ci] Prepare dummy control policy (64x4)"
mkdir -p artifacts/onnx
python scripts/inference/make_dummy_policy_onnx.py \
  --in-dim 64 --hidden 0 --out-dim 4 \
  --out artifacts/onnx/policy_dummy.onnx

echo "[ns-ci] Contents of artifacts/onnx/"
ls -l artifacts/onnx || true

echo "[ns-ci] Ready."
