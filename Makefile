.RECIPEPREFIX := >
.DEFAULT_GOAL := help

.PHONY: help onnx-all onnx-verify onnx-deploy-smoke stack-smoke data-verify data-diff integrity-summary ci

help:
> @echo "Targets:"
> @echo "  onnx-all           contracts+perf+offline smokes"
> @echo "  onnx-verify        verify deploy manifest hashes"
> @echo "  onnx-deploy-smoke  ORT-load models from deploy manifest"
> @echo "  stack-smoke        depth+policy quick demo"
> @echo "  data-verify        dataset manifest verify"
> @echo "  data-diff          dataset manifest diff vs baseline"
> @echo "  integrity-summary  emit release integrity JSON"
> @echo "  ci                 run all gates"

onnx-all:
> python scripts/inference/check_onnx_contracts.py --config docs/perf/budgets.yaml --outdir artifacts/perf
> python scripts/inference/profile_onnx.py --config docs/perf/budgets.yaml --outdir artifacts/perf --check
> pytest -q training/tests/inference/test_depth_offline_smoke.py \
>          training/tests/inference/test_policy_offline_smoke.py \
>          training/tests/inference/test_e2e_tick_smoke.py \
>          training/tests/inference/test_promote_model_smoke.py

onnx-verify:
> python scripts/inference/verify_manifest_hashes.py --manifest deploy/models/manifest.json --check

onnx-deploy-smoke:
> pytest -q training/tests/inference/test_deploy_manifest_smoke.py

stack-smoke:
> python scripts/inference/stack_demo.py

data-verify:
> python scripts/datasets/verify_manifest.py --root datasets --manifest datasets/manifest.json

data-diff:
> python scripts/datasets/manifest.py --root datasets --out datasets/manifest.json
> python scripts/datasets/diff_manifest.py --old docs/perf/baselines/datasets_manifest_baseline.json --new datasets/manifest.json

integrity-summary:
> python scripts/inference/integrity_summary.py --manifest deploy/models/manifest.json --out artifacts/releases/integrity_summary.json

ci:
> $(MAKE) onnx-all
> $(MAKE) onnx-verify
> $(MAKE) onnx-deploy-smoke
> $(MAKE) stack-smoke
> $(MAKE) data-verify
> $(MAKE) data-diff
> $(MAKE) integrity-summary
# === domain-rand & data smoke additions ===
.PHONY: rand-profile data-checksums

rand-profile:
> python simulation/domain_randomization/scripts/apply_randomization.py \
>   --profile sim/simulation/domain_randomization/profiles/minimal.yaml \
>   --out artifacts/domain_randomization/minimal.json

data-checksums:
> mkdir -p artifacts/datasets
> python sim/scripts/data/hash_tree.py datasets > artifacts/datasets/artifacts.sha256 || true
> test -s artifacts/datasets/artifacts.sha256 && echo "Checksums written"

# === Domain Randomization ===
.PHONY: rand-sweep
rand-sweep:
> mkdir -p artifacts/domain_randomization
> python simulation/domain_randomization/scripts/apply_randomization.py \
>   --profile sim/simulation/domain_randomization/profiles/$(PROFILE).yaml \
>   --out artifacts/domain_randomization/$(PROFILE).json \
>   --jsonl artifacts/domain_randomization/$(PROFILE)-samples.jsonl


# === Maps/Costmaps ===
.PHONY: maps-costmap
maps-costmap:
> AREA=$(AREA) ./scripts/maps/make_costmap.sh
