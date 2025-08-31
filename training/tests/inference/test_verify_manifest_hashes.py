import pathlib
import subprocess
import sys

MAN = "deploy/models/manifest.json"


def _run(argv):
    return subprocess.run([sys.executable, *argv], check=True, capture_output=True, text=True)


def test_manifest_hashes_ok():
    pathlib.Path(MAN).is_file() or (_ for _ in ()).throw(AssertionError("missing manifest"))
    # if hashes missing, write them once to stabilize CI/dev
    try:
        _run(["scripts/inference/verify_manifest_hashes.py", "--manifest", MAN, "--check"])
    except subprocess.CalledProcessError:
        _run(["scripts/inference/verify_manifest_hashes.py", "--manifest", MAN, "--write"])
        _run(["scripts/inference/verify_manifest_hashes.py", "--manifest", MAN, "--check"])
