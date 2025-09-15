# ruff: noqa: E501
import json
import subprocess
from pathlib import Path


def test_world_patch(tmp_path: Path):
    prof = {"wind_mps": 5.0, "direction_deg": 90.0}
    (tmp_path / "last_profile.json").write_text(json.dumps(prof))
    tmpl = """<sdf version="1.8"><world><plugin name="gz::sim::systems::Wind"><linear_velocity>__WIND_X__ __WIND_Y__ __WIND_Z__</linear_velocity></plugin></world></sdf>"""
    (tmp_path / "base.tmpl").write_text(tmpl)
    out = tmp_path / "world_dr.sdf"

    subprocess.run(
        [
            "python",
            "scripts/sim/apply_dr_to_gz.py",
            "--profile",
            str(tmp_path / "last_profile.json"),
            "--template",
            str(tmp_path / "base.tmpl"),
            "--out",
            str(out),
        ],
        check=True,
    )

    text = out.read_text()
    assert "NORTHSTRIKE-DR-APPLIED" in text
    assert "wx=0.0" in text or "wx=0" in text
    assert "wy=5.0" in text or "wy=5" in text
