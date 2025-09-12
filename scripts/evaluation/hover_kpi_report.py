#!/usr/bin/env python3
from __future__ import annotations
import argparse, csv, json, math
from pathlib import Path

def _pick(row, *ks):
    for k in ks:
        if k in row: return float(row[k])
    return 0.0

def compute_hover_kpis(df=None, csv_path=None, radius:float=0.5, dt:float|None=None):
    rows = (df.to_dict("records") if hasattr(df,"to_dict")
            else (list(csv.DictReader(open(csv_path))) if csv_path else (df or [])))
    n = len(rows)
    if n==0:
        return {"samples":0,"duration_s":0.0,"alt_mean":0.0,"alt_std":0.0,"alt_rmse":0.0,
                "max_alt_dev":0.0,"xy_std":0.0,"xy_rms_m":0.0,"hover_rms_m":0.0,"hover_score":1.0}
    dt_fallback = dt if dt is not None else 0.03
    ts = [float(r["t"]) if "t" in r else i*dt_fallback for i,r in enumerate(rows)]
    xs = [_pick(r,"px","x","ekf_px") for r in rows]
    ys = [_pick(r,"py","y","ekf_py") for r in rows]
    zs = [_pick(r,"rel_alt_m","z","abs_alt_m") for r in rows]
    def _mean(a): return sum(a)/len(a)
    def _std(a):
        m=_mean(a); return math.sqrt(_mean([(v-m)**2 for v in a]))
    err = [math.hypot(x,y) for x,y in zip(xs,ys)]
    alt_mean = _mean(zs)
    alt_std = _std(zs)
    alt_rmse = math.sqrt(_mean([(z-alt_mean)**2 for z in zs]))
    xy_std = _std(err)
    xy_rms = math.sqrt(_mean([e*e for e in err]))
    score = max(0.0, 1.0 - xy_rms/max(2*radius,0.5))
    return {"samples":n,"duration_s":ts[-1]-ts[0],
            "alt_mean":alt_mean,"alt_std":alt_std,"alt_rmse":alt_rmse,
            "max_alt_dev":max(abs(z-alt_mean) for z in zs),
            "xy_std":xy_std,"xy_rms_m":xy_rms,"hover_rms_m":xy_rms,"hover_score":score}

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--csv",required=True)
    p.add_argument("--json-out",required=True)
    p.add_argument("--radius",type=float,default=0.5)
    p.add_argument("--dt",type=float,default=None)
    a=p.parse_args()
    res = compute_hover_kpis(csv_path=a.csv, radius=a.radius, dt=a.dt)
    Path(a.json_out).write_text(json.dumps(res,indent=2))
    print(f"Wrote {a.json_out}")
if __name__=="__main__": main()
