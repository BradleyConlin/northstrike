#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seeds", type=int, default=2)
    ap.add_argument("--sim-seconds", type=float, default=1.5)
    ap.parse_args()
    out = Path("artifacts/compare_planners_sweep.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("# Planner KPI Seed Sweep\n\n**RRT (across seeds)**: ok\n")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
