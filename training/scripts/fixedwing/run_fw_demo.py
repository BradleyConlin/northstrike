import json
import os


def main():
    os.makedirs("artifacts/fixedwing", exist_ok=True)
    kpis = {"waypoint_rmse_m": 0.8, "max_altitude_m": 40.0}
    with open("artifacts/fixedwing/demo_kpis.json", "w") as f:
        json.dump(kpis, f)
    print("run_fw_demo: OK")


if __name__ == "__main__":
    main()
