#!/usr/bin/env python3
import argparse, json, statistics, time
def main():
    p = argparse.ArgumentParser()
    p.add_argument("--episodes", type=int, default=3)
    p.add_argument("--out", required=True)
    a = p.parse_args()
    # deterministic pseudo-returns
    totals = [round(45.0 + i * (5.0 + 0.5 * i), 2) for i in range(a.episodes)]
    data = {
        "mode": "smoke",
        "episodes": a.episodes,
        "totals": totals,
        "p50_return": statistics.median(totals),
        "ts": int(time.time()),
    }
    with open(a.out, "w") as f:
        json.dump(data, f)
    print(json.dumps(data))
if __name__ == "__main__":
    main()
