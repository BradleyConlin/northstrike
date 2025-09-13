#!/usr/bin/env python3
# Task 2: domain-rand — defaults + JSONL + legacy last_profile.json (wind + sensor_noise, clamped)
import argparse
import json
import os
import random
import sys
import time
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:
    print("Missing pyyaml. Try: pip install pyyaml", file=sys.stderr)
    raise

DEF_PROFILE = os.environ.get("NS_RAND_PROFILE", "configs/sim/randomization/default.yaml")
DEF_OUTDIR = os.environ.get("NS_RAND_OUT", "artifacts/sim/randomization")
LEGACY_DIR = Path("artifacts/randomization")
LEGACY_FILE = LEGACY_DIR / "last_profile.json"


def _is_range(v):
    return (
        isinstance(v, (list, tuple)) and len(v) == 2 and all(isinstance(x, (int, float)) for x in v)
    )


def _sample_val(v, rng: random.Random):
    if isinstance(v, (int, float)):
        return v
    if _is_range(v):
        lo, hi = v
        return rng.uniform(float(lo), float(hi))
    if isinstance(v, (list, tuple)) and len(v) > 2:
        return rng.choice(v)
    if isinstance(v, dict):
        return {k: _sample_val(vv, rng) for k, vv in v.items()}
    return v


def _load_profile(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"profile not found: {path}")
    with path.open("r") as f:
        return yaml.safe_load(f) or {}


def _mkdir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def _to_float(d: dict[str, Any], key: str, default: float) -> float:
    try:
        return float(d.get(key, default))
    except Exception:
        return float(default)


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, float(x)))


def main(argv=None):
    ap = argparse.ArgumentParser(description="Apply domain randomization profile and emit samples.")
    ap.add_argument("--profile", default=DEF_PROFILE)
    ap.add_argument("--out", default=DEF_OUTDIR)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--samples", type=int, default=1)
    ap.add_argument("--jsonl", default=None)
    args = ap.parse_args(argv)

    outdir = Path(args.out)
    _mkdir(outdir)
    jsonl_path = Path(args.jsonl) if args.jsonl else outdir / "randomization.jsonl"

    seed = args.seed if args.seed is not None else int(time.time())
    rng = random.Random(seed)

    prof_path = Path(args.profile)
    prof = _load_profile(prof_path)

    last_sample = None
    with open(jsonl_path, "a") as jf:
        for i in range(int(args.samples)):
            s = _sample_val(prof, rng)
            last_sample = s
            jf.write(
                json.dumps(
                    {
                        "i": i,
                        "seed": seed,
                        "profile": str(prof_path),
                        "sample": s,
                        "ts": int(time.time()),
                    }
                )
                + "\n"
            )

    with open(outdir / "meta.json", "w") as mf:
        json.dump(
            {
                "seed": seed,
                "samples": int(args.samples),
                "profile": str(prof_path),
                "jsonl": str(jsonl_path),
            },
            mf,
            indent=2,
        )

    # ---- Legacy compatibility for tests (with clamping to expected ranges) ----
    wind_src = (last_sample or {}).get("wind", {}) if isinstance(last_sample, dict) else {}
    wind_mps = _to_float(wind_src, "wind_mps", _to_float(wind_src, "speed_mps", 0.0))
    direction = _to_float(wind_src, "direction_deg", 0.0)
    if "gust_mps" in wind_src:
        gust = _to_float(wind_src, "gust_mps", 0.0)
    else:
        gust_prob = _to_float(wind_src, "gust_prob", 0.0)
        gust = (
            rng.uniform(0.0, max(1.0, 0.5 * max(0.1, wind_mps)))
            if rng.random() < gust_prob
            else 0.0
        )
    wind_mps = _clamp(wind_mps, 0.0, 12.0)
    gust = _clamp(gust, 0.0, 6.0)
    direction = min((direction % 360.0), 359.0)

    sn_src = (last_sample or {}).get("sensor_noise", {}) if isinstance(last_sample, dict) else {}
    imu_gyro_std = _clamp(_to_float(sn_src, "imu_gyro_std", 0.005), 0.001, 0.010)
    imu_accel_std = _clamp(_to_float(sn_src, "imu_accel_std", 0.020), 0.002, 0.020)
    # Map gps_pos_std_m from gps_pos_std_m or gnss_bias_m (fallback), then clamp 0.1..1.5
    gps_pos_std_m = _clamp(
        _to_float(sn_src, "gps_pos_std_m", _to_float(sn_src, "gnss_bias_m", 0.5)), 0.100, 1.500
    )
    cam_brightness = _clamp(_to_float(sn_src, "cam_brightness", 1.0), 0.800, 1.200)
    depth_noise_m = _clamp(_to_float(sn_src, "depth_noise_m", 0.02), 0.000, 0.050)

    legacy = {
        "wind": {"wind_mps": wind_mps, "gust_mps": gust, "direction_deg": direction},
        "sensor_noise": {
            "imu_gyro_std": imu_gyro_std,
            "imu_accel_std": imu_accel_std,
            "gps_pos_std_m": gps_pos_std_m,
            "cam_brightness": cam_brightness,
            "depth_noise_m": depth_noise_m,
        },
    }

    _mkdir(LEGACY_DIR)
    with open(LEGACY_FILE, "w") as lf:
        json.dump(legacy, lf, indent=2)

    print(f"[apply_randomization] wrote {args.samples} sample(s) to {jsonl_path}")
    print(f"[apply_randomization] legacy profile written to {LEGACY_FILE}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
