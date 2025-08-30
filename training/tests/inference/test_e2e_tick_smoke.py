import json, os, subprocess, sys

OUT = "artifacts/perf/e2e_tick.json"

def test_e2e_tick_creates_report():
    try:
        os.remove(OUT)
    except FileNotFoundError:
        pass
    subprocess.run(
        [sys.executable, "scripts/inference/e2e_tick.py", "--iters", "2", "--out", OUT],
        check=True,
    )
    assert os.path.isfile(OUT)
    d = json.loads(open(OUT).read())
    assert d["depth_input_shape"] == [1, 3, 384, 640]
    assert d["depth_output_shape"][0] == 1 and d["depth_output_shape"][1] == 1
    assert d["policy_input_shape"] == [1, 64]
    assert d["policy_output_shape"][0] == 1
