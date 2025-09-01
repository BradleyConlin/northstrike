import pathlib
import subprocess
import sys


def run(args):
    return subprocess.run([sys.executable, *args], check=True, capture_output=True, text=True)


def write(p, txt):
    pathlib.Path(p).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(p).write_text(txt)


def test_dataset_manifest_diff(tmp_path):
    root = tmp_path / "d"
    (root / "a").mkdir(parents=True)
    write(root / "a" / "x.txt", "v1")
    run(["scripts/datasets/manifest.py", "--root", str(root), "--out", str(tmp_path / "m1.json")])
    # modify + add + remove
    write(root / "a" / "x.txt", "v2")
    write(root / "a" / "y.txt", "new")
    (root / "a" / "x2.txt").write_text("gone")
    (root / "a" / "x2.txt").unlink()
    run(["scripts/datasets/manifest.py", "--root", str(root), "--out", str(tmp_path / "m2.json")])
    r = run(
        [
            "scripts/datasets/diff_manifest.py",
            "--old",
            str(tmp_path / "m1.json"),
            "--new",
            str(tmp_path / "m2.json"),
        ]
    )
    out = r.stdout
    assert "ADDED    a/y.txt" in out
    assert "MOD      a/x.txt" in out
