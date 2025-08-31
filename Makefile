.RECIPEPREFIX := >

# --- ONNX gates ---
onnx-all:
> python scripts/inference/check_onnx_contracts.py --config docs/perf/budgets.yaml --outdir artifacts/perf
> python scripts/inference/profile_onnx.py --config docs/perf/budgets.yaml --outdir artifacts/perf --check
> pytest -q training/tests/inference/test_depth_offline_smoke.py training/tests/inference/test_policy_offline_smoke.py training/tests/inference/test_e2e_tick_smoke.py training/tests/inference/test_promote_model_smoke.py

onnx-regress:
> python scripts/inference/depth_regress.py --model artifacts/onnx/depth_e24.onnx --out-json artifacts/perf/depth_regress_baseline.json

onnx-deploy-smoke:
> pytest -q training/tests/inference/test_deploy_manifest_smoke.py

onnx-verify:
> python scripts/inference/verify_manifest_hashes.py --manifest deploy/models/manifest.json --check

# --- Dataset integrity ---
data-scan:
> python scripts/datasets/manifest.py --root datasets --out datasets/manifest.json

data-verify:
> python scripts/datasets/verify_manifest.py --root datasets --manifest datasets/manifest.json

data-diff:
> python scripts/datasets/manifest.py --root datasets --out datasets/manifest.json
> python scripts/datasets/diff_manifest.py --old docs/perf/baselines/datasets_manifest_baseline.json --new datasets/manifest.json

stack-smoke:
	python scripts/inference/stack_demo.py
