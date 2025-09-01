#!/usr/bin/env python3
import argparse
import json
import math
import sys


def load(p):
    with open(p) as f:
        return json.load(f)


def pct(a, b):
    if a == 0:
        return math.inf if b > 0 else 0.0
    return (b - a) / a * 100.0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--baseline-e2e", required=True)
    ap.add_argument("--current-e2e", required=True)
    ap.add_argument("--max-regress-pct", type=float, default=20.0)  # allow up to +20%
    args = ap.parse_args()

    base = load(args.baseline_e2e)
    curr = load(args.current_e2e)

    fields = ["p50_depth_ms", "p50_policy_ms"]
    bad = []
    for k in fields:
        if k not in base or k not in curr:
            print(f"[WARN] missing key {k} in baseline/current")
            continue
        r = pct(base[k], curr[k])
        mark = "OK"
        if r > args.max_regress_pct + 1e-9:
            bad.append((k, base[k], curr[k], r))
            mark = "FAIL"
        print(
            f"[drift] {k}: baseline={base[k]:.6f} current={curr[k]:.6f} regress={r:+.1f}%  {mark}"
        )

    if bad:
        print("\n[ERROR] perf regression exceeds threshold:")
        for k, a, b, r in bad:
            print(f"  - {k}: {a:.6f} -> {b:.6f}  (+{r:.1f}%) > {args.max_regress_pct}%")
        sys.exit(2)
    print("[drift] within thresholds")
    return 0


if __name__ == "__main__":
    sys.exit(main())
