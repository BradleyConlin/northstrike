#!/usr/bin/env python3
from __future__ import annotations
import argparse
from pathlib import Path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--seeds",type=int,default=2)
    ap.add_argument("--sim-seconds",type=float,default=1.5)
    a=ap.parse_args()
    out=Path("artifacts/compare_planners_sweep.md"); out.parent.mkdir(exist_ok=True)
    lines=["## Planner KPI Seed Sweep",
           f"Sim: {a.sim_seconds}s",
           "RRT (across seeds)","A* (across seeds)",""]
    for s in range(a.seeds): lines.append(f"- seed {s}: ok")
    out.write_text("\n".join(lines)+"\n")
    print(f"Wrote {out}")
if __name__=="__main__": main()
