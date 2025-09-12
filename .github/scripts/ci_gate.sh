#!/usr/bin/env bash
set -Eeuo pipefail

echo "[ci-gate] setup python & deps"
python -m pip install -U pip >/dev/null
[ -f requirements.txt ] && pip install -r requirements.txt >/dev/null
[ -f requirements-perf.txt ] && pip install -r requirements-perf.txt >/dev/null

echo "[ci-gate] hydrate LFS (if present)"
git lfs fetch --all >/dev/null 2>&1 || true
git lfs checkout >/dev/null 2>&1 || true

echo "[ci-gate] run tests"
pytest -q

echo "[ci-gate] onnx verify"
if grep -q '^onnx-verify:' Makefile; then
  make onnx-verify
else
  echo "Make target onnx-verify not found, skipping."
fi

echo "[ci-gate] done"
