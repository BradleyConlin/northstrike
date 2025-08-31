set -euo pipefail
python scripts/inference/check_onnx_contracts.py --config docs/perf/budgets.yaml --outdir artifacts/perf
python scripts/inference/profile_onnx.py --config docs/perf/budgets.yaml --outdir artifacts/perf --check
python scripts/inference/e2e_tick.py --out artifacts/perf/e2e_tick.json
python scripts/inference/perf_drift_check.py \
  --baseline-e2e docs/perf/baselines/e2e_tick_baseline.json \
  --current-e2e artifacts/perf/e2e_tick.json --max-regress-pct 20
