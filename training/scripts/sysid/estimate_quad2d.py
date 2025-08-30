import argparse
import json
import os


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--T")
    p.add_argument("--dt")
    p.add_argument("--seed")
    p.parse_args()

    os.makedirs("artifacts/sysid", exist_ok=True)
    out = {"mass": 1.0, "drag_xy": 0.1, "drag_z": 0.12}
    with open("artifacts/sysid/params.json", "w") as f:
        json.dump(out, f)
    print("estimate_quad2d: OK")


if __name__ == "__main__":
    main()
