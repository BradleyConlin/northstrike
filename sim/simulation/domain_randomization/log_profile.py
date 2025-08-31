#!/usr/bin/env python3
import argparse, json, os, random, time
def make_profile(seed):
    r=random.Random(seed)
    return {
        "seed": seed, "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "wind": {"speed": round(r.uniform(0,8),2), "direction_deg": r.randrange(0,360)},
        "lighting": {"sun_elev_deg": r.randrange(5,85), "cloud": round(r.uniform(0,1),2)},
        "textures": {"variant": r.choice(["a","b","c"])},
        "sensors": {"imu_bias": round(r.uniform(-0.02,0.02),4),
                    "gnss_bias_m": round(r.uniform(-3,3),2),
                    "noise": round(r.uniform(0,0.01),4)}
    }
if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default=None)
    a=ap.parse_args()
    prof=make_profile(a.seed)
    out=a.out or f"artifacts/randomization/profile_{a.seed}.json"
    os.makedirs(os.path.dirname(out), exist_ok=True)
    json.dump(prof, open(out, "w"), indent=2)
    print(f"[rand] wrote {out}")
