import argparse
import csv
import json
import os

import mlflow
import numpy as np


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    parser.parse_args()

    os.makedirs("artifacts/training", exist_ok=True)

    # tiny "model" + metrics CSV for tests
    np.savez("artifacts/training/model_dummy.npz", w=[1, 2, 3])
    with open("artifacts/training/metrics.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["epoch", "loss", "acc"])
        w.writerow([0, 1.0, 0.40])
        w.writerow([1, 0.5, 0.80])

    # summary JSON expected by test_mlflow_tracking
    with open("artifacts/training/summary.json", "w") as f:
        json.dump({"epochs": 2, "loss": 0.5, "acc": 0.8}, f)

    # simple MLflow roundtrip
    mlflow.set_tracking_uri("file:" + os.path.abspath("mlruns"))
    mlflow.set_experiment("northstrike-ci")
    with mlflow.start_run():
        mlflow.log_param("epochs", 2)
        mlflow.log_metric("loss", 0.5)
        mlflow.log_metric("acc", 0.8)
        mlflow.log_artifact("artifacts/training/metrics.csv")

    print("train_dummy: OK")


if __name__ == "__main__":
    main()
