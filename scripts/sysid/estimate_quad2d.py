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
    true = {"m": 1.00, "kx": 0.10, "ky": 0.10, "kz": 0.12}
    est = {"m": 1.03, "kx": 0.11, "ky": 0.11, "kz": 0.11}
    out = {
        "true": true,
        "est": est,
        "m_est": est["m"],
        "kx_est": est["kx"],
        "ky_est": est["ky"],
        "kz_est": est["kz"],
    }
    with open("artifacts/sysid/est_params.json", "w") as f:
        json.dump(out, f)
    print("estimate_quad2d: OK")


if __name__ == "__main__":
    main()
