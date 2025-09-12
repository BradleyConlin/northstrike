#!/usr/bin/env python3
import argparse
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

try:
    import yaml  # PyYAML
except Exception:
    print("Please: pip install pyyaml", file=sys.stderr)
    sys.exit(2)

Number = int | float
Range = tuple[Number, Number] | list[Number]


def _rng_sample(v):
    if isinstance(v, int | float):
        return float(v)
    if isinstance(v, list | tuple) and len(v) == 2 and all(isinstance(x, int | float) for x in v):
        lo, hi = float(v[0]), float(v[1])
        return random.uniform(lo, hi)
    return v  # strings/arrays pass through


def _sample_point_lights(cfg):
    pl = cfg.get("point_lights") or {}
    count = int(round(_rng_sample(pl.get("count", [0, 0]))))
    out = []
    for _ in range(max(0, count)):
        out.append(
            {
                "intensity": _rng_sample(pl.get("intensity", [1.0, 2.0])),
                "x": random.uniform(-50, 50),
                "y": random.uniform(-50, 50),
                "z": random.uniform(5, 20),
            }
        )
    return out


def sample_once(profile: dict[str, Any]) -> dict[str, Any]:
    lighting = profile.get("lighting") or {}
    sun = lighting.get("sun") or {}
    res = {
        "name": profile.get("name", "profile"),
        "textures": {
            "ground": random.choice((profile.get("textures") or {}).get("ground", ["asphalt"])),
            "buildings": random.choice(
                (profile.get("textures") or {}).get("buildings", ["concrete"])
            ),
        },
        "lighting": {
            "sun": {
                "azimuth_deg": _rng_sample(sun.get("azimuth_deg", [0, 360])),
                "elevation_deg": _rng_sample(sun.get("elevation_deg", [10, 60])),
                "intensity": _rng_sample(sun.get("intensity", [0.5, 1.2])),
            },
            "ambient": _rng_sample(lighting.get("ambient", [0.2, 0.6])),
            "point_lights": _sample_point_lights(lighting),
        },
        "wind": {
            "mean_speed_mps": _rng_sample(
                (profile.get("wind") or {}).get("mean_speed_mps", [0, 5])
            ),
            "gust_speed_mps": _rng_sample(
                (profile.get("wind") or {}).get("gust_speed_mps", [0, 2])
            ),
            "direction_deg": _rng_sample(
                (profile.get("wind") or {}).get("direction_deg", [0, 360])
            ),
        },
        "sensors": {
            "imu": {
                "gyro_noise_std": _rng_sample(
                    ((profile.get("sensors") or {}).get("imu") or {}).get("gyro_noise_std", 0.006)
                ),
                "gyro_bias_rw": _rng_sample(
                    ((profile.get("sensors") or {}).get("imu") or {}).get("gyro_bias_rw", 0.0002)
                ),
                "accel_noise_std": _rng_sample(
                    ((profile.get("sensors") or {}).get("imu") or {}).get("accel_noise_std", 0.02)
                ),
                "accel_bias_rw": _rng_sample(
                    ((profile.get("sensors") or {}).get("imu") or {}).get("accel_bias_rw", 0.0005)
                ),
            },
            "gnss": {
                "pos_noise_std_m": _rng_sample(
                    ((profile.get("sensors") or {}).get("gnss") or {}).get("pos_noise_std_m", 1.5)
                ),
                "vel_noise_std_mps": _rng_sample(
                    ((profile.get("sensors") or {}).get("gnss") or {}).get("vel_noise_std_mps", 0.2)
                ),
            },
        },
        "ts": int(time.time() * 1000),
        "seed": random.randint(0, 2**31 - 1),
    }
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", required=True, help="YAML profile path")
    ap.add_argument("--out", required=True, help="JSON output (last sample)")
    ap.add_argument("--samples", type=int, default=None, help="override number of samples")
    ap.add_argument("--jsonl", default=None, help="optional JSONL sweep output")
    args = ap.parse_args()

    cfg = yaml.safe_load(Path(args.profile).read_text())
    n = int(args.samples or cfg.get("samples", 10))
    random.seed(os.environ.get("NS_RAND_SEED", str(int(time.time()))))

    outdir = Path(args.out).parent
    outdir.mkdir(parents=True, exist_ok=True)
    sweep = Path(args.jsonl) if args.jsonl else None
    if sweep:
        sweep.parent.mkdir(parents=True, exist_ok=True)

    last = None
    for _ in range(n):
        s = sample_once(cfg)
        last = s
        if sweep:
            with sweep.open("a") as f:
                f.write(json.dumps(s) + "\n")
    Path(args.out).write_text(json.dumps(last, indent=2))
    print(f"Wrote {args.out}" + (f" and {sweep}" if sweep else ""))


if __name__ == "__main__":
    sys.exit(main())
