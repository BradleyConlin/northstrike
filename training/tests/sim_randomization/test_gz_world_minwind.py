import json
import re
from pathlib import Path

from scripts.sim.apply_dr_to_gz import render_world


def test_min_wind_clamp(tmp_path: Path):
    prof = tmp_path / "last_profile.json"
    prof.write_text(json.dumps({"wind_mps": 0.0, "direction_deg": 90.0}))
    tmpl = tmp_path / "world.sdf.tmpl"
    tmpl.write_text(
        "<sdf version='1.8'><world name='w'><!-- NORTHSTRIKE-DR-TEMPLATE --></world></sdf>"
    )
    out = tmp_path / "world.sdf"
    render_world(prof, tmpl, out, min_wind_mps=3.0)
    txt = out.read_text()
    m = re.search(r"<linear_velocity>\s*([-0-9.]+)\s+([-0-9.]+)\s+0\.0</linear_velocity>", txt)
    assert m, "linear_velocity not injected"
    vx, vy = float(m.group(1)), float(m.group(2))
    assert abs((vx**2 + vy**2) ** 0.5 - 3.0) < 1e-3
