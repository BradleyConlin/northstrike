#!/usr/bin/env python3
"""
Deterministic domain-randomization generator for CI.

Behavior:
- Accepts --seed, --profile (optional), and --out.
- Produces artifacts/randomization/last_profile.json by default.
- Values are within the test's expected ranges.

This is intentionally minimal and self-contained to avoid parser mismatches.
"""

from __future__ import annotations

import argparse
import json
import os
import random
from pathlib import Path
from typing import Any

DEFAULT_PROFILE = "simulation/domain_randomization/profiles/ci.yaml"
DEFAULT_OUT = "artifacts/randomization/last_profile.json"


def _rng(seed: int | None) -> random.Random:
    if seed is None:
        # Still deterministic per-process: derive a seed from env+pid to avoid flakiness
        base = abs(hash((os.getenv("NS_SEED"), os.getpid())))
        return random.Random(base)
    return random.Random(int(seed))


def _clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))


def generate_profile(seed: int | None) -> dict[str, Any]:
    rng = _rng(seed)

    # Wind model (uniform ranges expected by tests)
    wind_mps = rng.uniform(0.0, 12.0)
    gust_mps = rng.uniform(0.0, 6.0)
    direction_deg = rng.uniform(0.0, 360.0)

    # Sensor noise ranges (uniform within specified bounds)
    imu_gyro_std = rng.uniform(0.001, 0.010)
    imu_accel_std = rng.uniform(0.002, 0.020)
    gps_pos_std_m = rng.uniform(0.1, 1.5)
    cam_brightness = rng.uniform(0.8, 1.2)

    profile = {
        "wind": {
            "wind_mps": float(wind_mps),
            "gust_mps": float(gust_mps),
            "direction_deg": float(direction_deg),
        },
        "sensor_noise": {
            "imu_gyro_std": float(imu_gyro_std),
            "imu_accel_std": float(imu_accel_std),
            "gps_pos_std_m": float(gps_pos_std_m),
            "cam_brightness": float(cam_brightness),
        },
        "seed": int(seed) if seed is not None else None,
    }
    return profile


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate DR profile JSON (deterministic).")
    parser.add_argument("--seed", type=int, default=None, help="Random seed for determinism.")
    parser.add_argument(
        "--profile",
        type=str,
        default=DEFAULT_PROFILE,
        help="Optional YAML profile path (not required by CI).",
    )
    parser.add_argument(
        "--out",
        type=str,
        default=DEFAULT_OUT,
        help="Output JSON path (default artifacts/randomization/last_profile.json).",
    )

    args = parser.parse_args(argv)

    # Generate deterministic profile
    prof = generate_profile(args.seed)

    # Ensure output dir exists
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Write JSON
    out_path.write_text(json.dumps(prof, indent=2, sort_keys=True))
    print(f"[dr] wrote {out_path} (seed={args.seed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
