import subprocess
from pathlib import Path


def test_visual_dr_renders_world(tmp_path):
    out = Path("artifacts/sim/tmp/world_dr.sdf")
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "python",
        "scripts/sim/apply_dr_to_gz.py",
        "--profile",
        "configs/sim/randomization/visual_profile.json",
        "--template",
        "simulation/domain_randomization/assets/base_airfield.sdf.tmpl",
        "--out",
        str(out),
        "--min-wind-mps",
        "2",
    ]
    subprocess.run(cmd, check=True)
    s = out.read_text()
    assert "<world name=" in s
    assert "<wind>" in s
    assert "<pbr>" in s
