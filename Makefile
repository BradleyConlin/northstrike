.RECIPEPREFIX := >
.PHONY: onnx-check onnx-perf onnx-e2e onnx-all onnx-promote onnx-deploy-smoke release-models

onnx-check:
> python scripts/inference/check_onnx_contracts.py --config docs/perf/budgets.yaml --outdir artifacts/perf

onnx-perf:
> python scripts/inference/profile_onnx.py --config docs/perf/budgets.yaml --outdir artifacts/perf --check

onnx-e2e:
> pytest -q training/tests/inference/test_e2e_tick_smoke.py

onnx-all:
> python scripts/inference/check_onnx_contracts.py --config docs/perf/budgets.yaml --outdir artifacts/perf
> python scripts/inference/profile_onnx.py --config docs/perf/budgets.yaml --outdir artifacts/perf --check
> pytest -q training/tests/inference/test_depth_offline_smoke.py training/tests/inference/test_policy_offline_smoke.py training/tests/inference/test_e2e_tick_smoke.py training/tests/inference/test_promote_model_smoke.py

onnx-promote:
> python scripts/inference/promote_model.py --config docs/perf/budgets.yaml --target perception.depth --model artifacts/onnx/depth_e24.onnx
> python scripts/inference/promote_model.py --config docs/perf/budgets.yaml --target control.policy   --model artifacts/onnx/policy_dummy.onnx

onnx-deploy-smoke:
> pytest -q training/tests/inference/test_deploy_manifest_smoke.py

release-models:
> make onnx-all
> python scripts/inference/e2e_tick.py --out artifacts/perf/e2e_tick.json
> git add deploy/models/manifest.json artifacts/perf/e2e_tick.json
> git commit -m "models: promote + gates green"
