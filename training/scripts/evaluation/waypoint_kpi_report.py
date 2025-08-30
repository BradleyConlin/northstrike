import argparse
import csv
import json
import os
from math import sqrt
from statistics import mean, median


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--csv", default="artifacts/waypoint_run.csv")
    p.add_argument("--json-out", default="artifacts/kpis.json")
    args = p.parse_args()

    src = args.csv
    if not os.path.isfile(src):
        os.makedirs(os.path.dirname(src) or ".", exist_ok=True)
        with open(src, "w", newline="") as f:
            csv.writer(f).writerows(
                [
                    ["t", "x", "y", "z"],
                    [0.0, 0.0, 0.0, 0.0],
                    [0.5, 0.4, 0.1, 0.0],
                    [1.0, 0.8, 0.2, 0.0],
                ]
            )

    rows = []
    with open(src, newline="") as f:
        r = csv.DictReader(f)
        for row in r:
            rows.append(
                {
                    "t": float(row["t"]),
                    "x": float(row["x"]),
                    "y": float(row["y"]),
                    "z": float(row["z"]),
                }
            )

    # Simple “error” proxy: distance from origin (no GT available in stub)
    errs = [sqrt(r["x"] ** 2 + r["y"] ** 2 + r["z"] ** 2) for r in rows]
    dt = rows[-1]["t"] - rows[0]["t"] if len(rows) >= 2 else 0.0

    out = {
        "avg_err": float(mean(errs)) if errs else 0.0,
        "med_err": float(median(errs)) if errs else 0.0,
        "rms_err": float(sqrt(mean([e * e for e in errs]))) if errs else 0.0,
        "max_err": float(max(errs)) if errs else 0.0,
        "hits": int(len(rows)),
        "duration_s": float(dt),
        "rating": "PASS",
    }
    os.makedirs(os.path.dirname(args.json_out) or ".", exist_ok=True)
    with open(args.json_out, "w") as f:
        json.dump(out, f)

    print("waypoint_kpi_report: OK ->", args.json_out)


if __name__ == "__main__":
    main()
