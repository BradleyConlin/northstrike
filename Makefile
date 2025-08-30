.RECIPEPREFIX := >
.PHONY: onnx-check onnx-perf onnx-e2e onnx-promote onnx-all

onnx-check:
> python scripts/inference/check_onnx_contracts.py --config docs/perf/budgets.yaml --outdir artifacts/perf

onnx-perf:
> python scripts/inference/profile_onnx.py --config docs/perf/budgets.yaml --outdir artifacts/perf --check

onnx-e2e:
> pytest -q training/tests/inference/test_e2e_tick_smoke.py

onnx-promote:
> pytest -q training/tests/inference/test_promote_model_smoke.py

onnx-all: onnx-check onnx-perf
> pytest -q \
>   training/tests/inference/test_depth_offline_smoke.py \
>   training/tests/inference/test_policy_offline_smoke.py \
>   training/tests/inference/test_e2e_tick_smoke.py \
>   training/tests/inference/test_promote_model_smoke.py
