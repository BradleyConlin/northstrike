.PHONY: depth_onnx_smoke
REPO?=$(HOME)/dev/northstrike-training
MODEL?=$(REPO)/weights/depth_dummy_e00_320x240.onnx
RGB_DIR?=/home/brad/dev/northstrike-linux-sim/datasets/sim_2025-08-22_122259_aug/rgb
GT_DIR?=/home/brad/dev/northstrike-linux-sim/datasets/sim_2025-08-22_122259_aug/depth
OUT?=$(REPO)/runs/depth_onnx_smoke_$(shell date +%F_%H%M)

depth_onnx_smoke:
	@python scripts/perception/depth_onnx_smoke.py --model "$(MODEL)" --rgb "$(RGB_DIR)" --gt "$(GT_DIR)" --out "$(OUT)" --width 320 --height 240 --max-images 50 --max-depth-m 20.0 --gt-scale 0.001 --pred-scale 20.0
	@echo "Artifacts → $(OUT)"
