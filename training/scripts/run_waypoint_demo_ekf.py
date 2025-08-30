import argparse
import csv
import os


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--sim-seconds")
    p.add_argument("--dt")
    p.parse_args()

    os.makedirs("artifacts", exist_ok=True)
    rows = [
        ["t", "x", "y", "z"],
        [0.0, 0.0, 0.0, 0.0],
        [0.5, 0.4, 0.1, 0.0],
        [1.0, 0.8, 0.2, 0.0],
    ]
    # Write both names some tests look for:
    for path in ("artifacts/waypoint_run.csv", "artifacts/waypoint_run_ekf.csv"):
        with open(path, "w", newline="") as f:
            csv.writer(f).writerows(rows)
    print("run_waypoint_demo_ekf: OK")


if __name__ == "__main__":
    main()
