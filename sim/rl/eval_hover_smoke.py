#!/usr/bin/env python3
import argparse, json, os, random, time

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--episodes", type=int, default=3)
    p.add_argument("--out", default="artifacts/rl/hover_eval.json")
    args = p.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    random.seed(0)
    totals = []
    for ep in range(args.episodes):
        steps = 50 + ep * 5
        rew = 0.0
        for t in range(steps):
            rew += 1.0 - 0.002 * t
        totals.append(rew)

    out = {
        "mode": "smoke",
        "episodes": args.episodes,
        "totals": totals,
        "p50_return": sorted(totals)[len(totals)//2],
        "ts": int(time.time()),
    }
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)
    print(f"[SMOKE] wrote {args.out}; totals={totals}")

if __name__ == "__main__":
    main()
