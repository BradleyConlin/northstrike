import json
import pathlib
import subprocess
import sys


def run(args): return subprocess.run([sys.executable,*args], check=True, capture_output=True, text=True)
def test_dataset_manifest_roundtrip(tmp_path):
    root=pathlib.Path("datasets"); root.mkdir(exist_ok=True, parents=True)
    # ensure at least one tiny file so test is meaningful
    (root/"_smoke").mkdir(exist_ok=True)
    p = root/"_smoke"/"tiny.txt"; p.write_text("northstrike")
    run(["scripts/datasets/manifest.py","--root","datasets","--out","datasets/manifest.json"])
    run(["scripts/datasets/verify_manifest.py","--root","datasets","--manifest","datasets/manifest.json"])
    man=json.load(open("datasets/manifest.json"))
    assert man["meta"]["total"]>=1
