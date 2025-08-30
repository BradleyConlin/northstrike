import argparse
import json
import os

import mlflow


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="configs/mlops/experiment.yaml")
    ap.parse_args()

    with open("artifacts/training/summary.json") as f:
        summary = json.load(f)

    mlflow.set_tracking_uri("file:" + os.path.abspath("mlruns"))
    # Ensure both exist, use 'northstrike' to satisfy tests
    for name in ("northstrike", "northstrike-ci"):
        mlflow.set_experiment(name)
    mlflow.set_experiment("northstrike")

    with mlflow.start_run() as run:
        mlflow.log_param("epochs", summary.get("epochs", 0))
        if "loss" in summary:
            mlflow.log_metric("loss", float(summary["loss"]))
        if "acc" in summary:
            mlflow.log_metric("acc", float(summary["acc"]))
        if os.path.isfile("artifacts/training/metrics.csv"):
            mlflow.log_artifact("artifacts/training/metrics.csv")
        print(f"logged run_id={run.info.run_id}")


if __name__ == "__main__":
    main()
