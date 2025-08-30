.RECIPEPREFIX := >
# Gates
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
# Deploy
onnx-promote:
> python scripts/inference/promote_model.py --config docs/perf/budgets.yaml --target perception.depth --model artifacts/onnx/depth_e24.onnx
> python scripts/inference/promote_model.py --config docs/perf/budgets.yaml --target control.policy   --model artifacts/onnx/policy_dummy.onnx
onnx-deploy-smoke:
> pytest -q training/tests/inference/test_deploy_manifest_smoke.py
release-local:
> python scripts/inference/e2e_tick.py --out artifacts/perf/e2e_tick.json
> python scripts/inference/pack_models.py --manifest deploy/models/manifest.json --out artifacts/releases/models-local.zip
release-tag:
> TAG=models-$(shell date +%Y-%m-%d)-r$$(date +%H%M%S); git tag -a $$TAG -m "release $$TAG"; git push origin $$TAG
