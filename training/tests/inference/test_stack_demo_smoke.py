import pathlib
import subprocess
import sys


def test_stack_demo_runs():
    pathlib.Path("deploy/models/manifest.json").is_file() or (_ for _ in ()).throw(
        AssertionError("missing manifest")
    )
    r = subprocess.run(
        [sys.executable, "scripts/inference/stack_demo.py"],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "[stack] depth" in r.stdout and "[stack] policy" in r.stdout
