.RECIPEPREFIX := >
.PHONY: onnx-check onnx-perf onnx-demos onnx-all

onnx-check:
> python scripts/inference/check_onnx_contracts.py --config docs/perf/budgets.yaml --outdir artifacts/perf

onnx-perf:
> python scripts/inference/profile_onnx.py --config docs/perf/budgets.yaml --outdir artifacts/perf --check

onnx-demos:
> python scripts/inference/run_policy_offline.py --model artifacts/onnx/policy_dummy.onnx --in-csv artifacts/perf/policy_inputs_demo.csv --out-csv artifacts/perf/policy_outputs_demo.csv
> python scripts/inference/run_depth_offline.py --model artifacts/onnx/depth_e24.onnx --mode rand --out-npz artifacts/perf/depth_out_demo.npz --out-csv artifacts/perf/depth_stats_demo.csv

onnx-all: onnx-check onnx-perf onnx-demos
