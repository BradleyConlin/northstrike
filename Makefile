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
> @echo "  rand-profile       apply minimal domain-rand profile"
> @echo "  rand-sweep         apply domain-rand PROFILE=..."
> @echo "  data-checksums     write datasets checksums"
> @echo "  maps-dem/buildings/costmap  map recipes via make.sh"
> @echo "  maps-verify        print mask hist + cost ranges"
> @echo "  mbtiles            build offline MBTiles (cost/mask)"
> @echo "  mbtiles-verify     check MBTiles metadata"
> @echo "  maps-publish       placeholder for publishing"
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

# --- maps targets ---
.PHONY: maps-dem maps-buildings maps-costmap maps-verify

maps-dem:
> scripts/maps/make.sh dem $${AREA} $${S} $${W} $${N} $${E}

maps-buildings:
> scripts/maps/make.sh buildings $${AREA} $${S} $${W} $${N} $${E}

maps-costmap:
> scripts/maps/make.sh costmap $${AREA}

# maps verify
maps-verify:
> gdalinfo -stats -hist maps/build/$${AREA}_buildings_mask.tif | sed -n '1,80p'
> { gdalinfo -stats maps/costmaps/$${AREA}_cost.tif 2>/dev/null || gdalinfo -mm maps/costmaps/$${AREA}_cost.tif 2>/dev/null || true; } | sed -n '1,80p'

# --- Maps / Tiles / MBTiles ---------------------------------------------------
AREA ?= yyz_downtown
MAPS_DIR := maps
BUILD_DIR := $(MAPS_DIR)/build
COST_DIR := $(MAPS_DIR)/costmaps
TILES_DIR := tiles
MBTILES_DIR := $(MAPS_DIR)/mbtiles

# Expect these RGBA rasters already exist from your pipeline:
COST_RGBA := $(COST_DIR)/$(AREA)_cost_rgba.tif
MASK_RGBA := $(BUILD_DIR)/$(AREA)_buildings_mask_rgba.tif

.PHONY: mbtiles
mbtiles: $(MBTILES_DIR)/$(AREA)_cost.mbtiles $(MBTILES_DIR)/$(AREA)_mask.mbtiles

$(MBTILES_DIR)/$(AREA)_cost.mbtiles: $(COST_RGBA)
> mkdir -p $(MBTILES_DIR)
> scripts/maps/mbtiles_from_raster.sh "$<" "$@"

$(MBTILES_DIR)/$(AREA)_mask.mbtiles: $(MASK_RGBA)
> mkdir -p $(MBTILES_DIR)
> scripts/maps/mbtiles_from_raster.sh "$<" "$@"

.PHONY: mbtiles-verify
mbtiles-verify: mbtiles
> @echo "Checking MBTiles metadata and zooms..."
> sqlite3 $(MBTILES_DIR)/$(AREA)_cost.mbtiles 'select name, value from metadata where name in ("minzoom","maxzoom","format","name","bounds");'
> sqlite3 $(MBTILES_DIR)/$(AREA)_mask.mbtiles 'select name, value from metadata where name in ("minzoom","maxzoom","format","name","bounds");'
> @echo "✔ MBTiles look OK"

.PHONY: maps-publish
maps-publish: mbtiles
> @echo "Publish step placeholder (rsync/gh-release/minio). Add your remote later."
> @echo "Artifacts in: $(MBTILES_DIR)"

.PHONY: maps-readback
maps-readback:
> python scripts/maps/smoke_cost_readback.py --cost maps/costmaps/$(AREA)_cost.tif --n 20 --out maps/reports/$(AREA)_readback.csv

.PHONY: maps-costmap2
maps-costmap2:
> AREA=$(AREA) ./scripts/maps/make_costmap.sh --yaml scripts/maps/cost_recipe.yaml

# --- 8-bit MBTiles (from VRT) -----------------------------------------------
.PHONY: mbtiles8
mbtiles8: $(MBTILES_DIR)/$(AREA)_cost8.mbtiles

$(MBTILES_DIR)/$(AREA)_cost8.mbtiles: $(COST_DIR)/$(AREA)_cost_8bit.vrt
> mkdir -p $(MBTILES_DIR)
> scripts/maps/mbtiles_from_raster.sh "$<" "$@"

# --- Parity smoke: 8-bit grayscale tile value ~= scaled Float32 cost ---------
N ?= 30
.PHONY: tiles-parity
tiles-parity: mbtiles8
> python scripts/maps/tile_parity_smoke.py \
>   --mbtiles $(MBTILES_DIR)/$(AREA)_cost8.mbtiles \
>   --cost $(COST_DIR)/$(AREA)_cost.tif \
>   --zoom 14 --n $(N) \
>   --out maps/reports/$(AREA)_tile_parity.csv

.PHONY: maps-ci
maps-ci:
> $(MAKE) maps-costmap2 AREA=$(AREA)
> $(MAKE) mbtiles8 AREA=$(AREA)
> $(MAKE) tiles-parity AREA=$(AREA) N=40
> $(MAKE) maps-readback AREA=$(AREA)

.PHONY: maps-bundle
maps-bundle: mbtiles8
> mkdir -p artifacts/maps
> zip -j artifacts/maps/$(AREA)_tiles_cost8.zip $(MBTILES_DIR)/$(AREA)_cost8.mbtiles

.PHONY: maps-publish
maps-publish: maps-bundle
> @echo "Bundle ready: artifacts/maps/$(AREA)_tiles_cost8.zip"
