#!/usr/bin/env python3
from __future__ import annotations
import argparse,csv,json,math
from pathlib import Path

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--csv",required=True)
    ap.add_argument("--json-out",required=True)
    a=ap.parse_args()
    rows=list(csv.DictReader(open(a.csv)))
    xs=[float(r["x"]) for r in rows]; ys=[float(r["y"]) for r in rows]
    vxs=[float(r["vx"]) for r in rows]; vys=[float(r["vy"]) for r in rows]
    ts=[float(r.get("t","0")) for r in rows] or [0.0]
    errs=[math.hypot(x,y) for x,y in zip(xs,ys)]
    avg=sum(errs)/len(errs) if errs else 0.0
    rms=math.sqrt(sum(e*e for e in errs)/len(errs)) if errs else 0.0
    med=sorted(errs)[len(errs)//2] if errs else 0.0
    out={"avg_err":avg,"med_err":med,"rms_err":rms,"max_err":max(errs) if errs else 0.0,
         "hits":len(rows),"duration_s":(ts[-1]-ts[0]) if ts else 0.0,"rating":"OK"}
    Path(a.json_out).write_text(json.dumps(out,indent=2)); print(f"Wrote {a.json_out}")
if __name__=="__main__": main()
