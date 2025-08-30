.RECIPEPREFIX := >
onnx-regress:
> python scripts/inference/depth_regress.py --model artifacts/onnx/depth_e24.onnx --out-json artifacts/perf/depth_regress_baseline.json
> python scripts/inference/depth_regress.py --model artifacts/onnx/depth_e24.onnx --check-against artifacts/perf/depth_regress_baseline.json
onnx-all:
> python scripts/inference/check_onnx_contracts.py --config docs/perf/budgets.yaml --outdir artifacts/perf
> python scripts/inference/profile_onnx.py --config docs/perf/budgets.yaml --outdir artifacts/perf --check
> pytest -q training/tests/inference/test_depth_offline_smoke.py training/tests/inference/test_policy_offline_smoke.py training/tests/inference/test_e2e_tick_smoke.py training/tests/inference/test_promote_model_smoke.py training/tests/inference/test_deploy_manifest_smoke.py training/tests/inference/test_depth_regress_smoke.py
