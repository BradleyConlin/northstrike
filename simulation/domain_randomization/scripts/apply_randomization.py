#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="simulation/domain_randomization/profiles/ci.yaml")
    ap.add_argument("--out", default="artifacts/randomization/last_profile.json")
    ap.add_argument("--samples", type=int, default=1)
    ap.add_argument("--jsonl", default=None)
    ap.add_argument("--seed", type=int, default=None)
    args = ap.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    def bounded(a, b):
        return a + (b - a) * random.random()

    wind = {
        "wind_mps": float(bounded(0, 12)),
        "gust_mps": float(bounded(0, 5)),
        "direction_deg": float(bounded(0, 360)),
    }
    sensor_noise = {
        "imu_gyro_std": float(bounded(0.001, 0.01)),
        "imu_accel_std": float(bounded(0.002, 0.02)),
        "gps_pos_std_m": float(bounded(0.1, 1.5)),
        "cam_brightness": float(bounded(0.8, 1.2)),
    }
    out = {"seed": args.seed, "profile": args.profile, "wind": wind, "sensor_noise": sensor_noise}
    outp = Path(args.out)
    outp.parent.mkdir(parents=True, exist_ok=True)
    outp.write_text(json.dumps(out, indent=2))
    print(f"Wrote {outp}")


if __name__ == "__main__":
    main()
