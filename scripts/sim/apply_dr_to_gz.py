#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Apply a DR profile to a Gazebo Sim SDF world.

- Direction semantics: "towards" in ENU (0°=+X/east, 90°=+Y/north)
- Injects SDFormat <wind><linear_velocity>x y z</linear_velocity></wind>
  at the <!-- NORTHSTRIKE-DR-TEMPLATE --> marker or right after <world ...>.
References:
  * SDFormat world wind (<wind><linear_velocity>): vector3, default 0 0 0
  * Gazebo world frame is ENU (East, North, Up)
"""
import argparse, json, math, sys
from pathlib import Path

MARKER = "<!-- NORTHSTRIKE-DR-TEMPLATE -->"

def _towards_enu(speed_mps: float, direction_deg: float):
    """0°=+X (east), 90°=+Y (north), returns (vx, vy, vz)."""
    th = math.radians(direction_deg)
    vx = speed_mps * math.cos(th)
    vy = speed_mps * math.sin(th)
    # squash signed zeros
    if abs(vx) < 1e-9: vx = 0.0
    if abs(vy) < 1e-9: vy = 0.0
    return vx, vy, 0.0

def render_world(profile_path: Path | str,
                 template_path: Path | str,
                 out_path: Path | str,
                 min_wind_mps: float = 0.0,
                 scale_wind: float = 1.0):
    profile_path = Path(profile_path)
    template_path = Path(template_path)
    out_path = Path(out_path)

    prof = json.loads(profile_path.read_text())
    speed = float(prof.get("wind_mps", 0.0)) * float(scale_wind)
    if speed < float(min_wind_mps):
        speed = float(min_wind_mps)
    direction = float(prof.get("direction_deg", 0.0))

    vx, vy, vz = _towards_enu(speed, direction)

    header = (
        f"<!-- NORTHSTRIKE-DR-APPLIED wind_mps={speed:.1f} "
        f"direction_deg={direction:.1f} wx={vx:.1f} wy={vy:.1f} wz=0.0 -->"
    )
    wind_block = (
        f"{header}\n"
        "    <wind>\n"
        f"      <linear_velocity>{vx:.1f} {vy:.1f} 0.0</linear_velocity>\n"
        "    </wind>"
    )

    text = template_path.read_text()
    if MARKER in text:
        text = text.replace(MARKER, MARKER + "\n    " + wind_block)
    else:
        # inject right after opening <world ...>
        idx = text.find("<world")
        if idx >= 0:
            close_idx = text.find(">", idx)
            if close_idx >= 0:
                text = text[: close_idx + 1] + "\n    " + wind_block + text[close_idx + 1 :]
            else:
                text = wind_block + "\n" + text
        else:
            text = wind_block + "\n" + text

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(text)
    print(f"✅ Wrote {out_path}")

def main():
    ap = argparse.ArgumentParser(description="Apply DR profile to Gazebo SDF world (towards / ENU).")
    ap.add_argument("--profile", required=True)
    ap.add_argument("--template", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--min-wind-mps", type=float, default=0.0)
    ap.add_argument("--scale-wind", type=float, default=1.0)
    args = ap.parse_args()
    render_world(args.profile, args.template, args.out,
                 min_wind_mps=args.min_wind_mps, scale_wind=args.scale_wind)

if __name__ == "__main__":
    sys.exit(main() or 0)
