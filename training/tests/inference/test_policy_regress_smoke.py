import sys, subprocess, json, pathlib
M = "artifacts/onnx/policy_dummy.onnx"
B = "artifacts/perf/policy_regress_baseline.json"

def _run(argv):
    r = subprocess.run([sys.executable, *argv], check=True, capture_output=True, text=True)
    return r

def test_policy_regress_roundtrip(tmp_path):
    pathlib.Path("artifacts/perf").mkdir(parents=True, exist_ok=True)
    _run(["scripts/inference/policy_regress.py","--model",M,"--out-json",B])
    _run(["scripts/inference/policy_regress.py","--model",M,"--out-json",B,
          "--check-against",B,"--tol-mean","1e-4","--tol-std","1e-4"])
    j = json.load(open(B))
    assert j["in_shape"] == [1,64] and j["out_shape"] == [4]
