#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv
from pathlib import Path
from training.scripts.run_waypoint_demo import HDR, synth

EKF_HDR = ["t","x","y","z","vx","vy","vz","px","py","ekf_px","ekf_py","wp_index","lat","lon","rel_alt_m"]

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--sim-seconds",type=float,default=2.0)
    ap.add_argument("--dt",type=float,default=0.02)
    ap.add_argument("--wp-radius",type=float,default=0.5)
    args=ap.parse_args()

    art=Path("artifacts"); art.mkdir(exist_ok=True,parents=True)
    raw = art/"waypoint_run.csv"
    if not raw.exists():
        rows = synth(max(10,int(args.sim_seconds/args.dt)), args.dt)
        with raw.open("w",newline="") as f:
            w=csv.writer(f); w.writerow(HDR); w.writerows(rows)

    rows=[]
    with raw.open("r",newline="") as f:
        r=csv.DictReader(f)
        for d in r:
            ekf_px = float(d["px"])+0.02
            ekf_py = float(d["py"])-0.02
            rows.append([d["t"],d["x"],d["y"],d["z"],d["vx"],d["vy"],d["vz"],
                         d["px"],d["py"],ekf_px,ekf_py,d["wp_index"],d["lat"],d["lon"],d["rel_alt_m"]])

    with (art/"waypoint_run_ekf.csv").open("w",newline="") as f:
        w=csv.writer(f); w.writerow(EKF_HDR); w.writerows(rows)
    print("Wrote artifacts/waypoint_run_ekf.csv")

if __name__=="__main__": main()
