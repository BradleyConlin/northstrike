# Jetson Perf Harness (ORT + TensorRT)

## Install bits on Jetson (JetPack)
sudo apt update
sudo apt install -y libnvinfer-bin   # installs /usr/src/tensorrt/bin/trtexec
/usr/src/tensorrt/bin/trtexec --version

## ONNX Runtime (CPU/GPU/TRT EP as available)
python3 scripts/inference/ort_profile.py --model artifacts/onnx/depth_e24.onnx --provider cpu --iters 50
python3 scripts/inference/ort_profile.py --model artifacts/onnx/policy_dummy.onnx --provider cpu --shape 1x64 --iters 200

# If your ORT build includes the TensorRT EP, you can switch --provider to tensorrt.

## TensorRT direct benchmark
bash scripts/inference/trtexec_bench.sh artifacts/onnx/depth_e24.onnx
bash scripts/inference/trtexec_bench.sh artifacts/onnx/policy_dummy.onnx

## Outputs
artifacts/perf/ort_*.json  # {p50_ms, p90_ms, profile_trace}
artifacts/perf/trtexec_*.json  # {avg_latency_ms, log}
