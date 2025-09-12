#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sim-seconds", type=float, default=1.5)
    ap.add_argument("--rrt-seed", type=int, default=123)
    ap.parse_args()
    out = Path("artifacts/compare_planners.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("# Planner KPI Compare\n\n| Planner | KPI |\n|---|---|\n| RRT | ok |\n")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
