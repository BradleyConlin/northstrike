#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import sys
import time

import mlflow
import onnx
from mlflow import onnx as mlflow_onnx
from mlflow.tracking import MlflowClient


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="perception.depth")
    ap.add_argument("--onnx", default="artifacts/onnx/depth_e24.onnx")
    ap.add_argument("--backend", default="sqlite:///artifacts/mlflow/mlflow.db")
    ap.add_argument("--stage", default="Staging")  # Staging|Production|None
    ap.add_argument("--alias", default=None)       # optional; defaults to stage.lower()
    args = ap.parse_args()

    if not os.path.exists(args.onnx):
        print(f"ERROR: missing ONNX at {args.onnx}", file=sys.stderr)
        sys.exit(2)

    # Ensure local DB folder exists (the .db file is created by MLflow on first use)
    os.makedirs("artifacts/mlflow", exist_ok=True)

    # Registry requires a DB-backed store; set both tracking & registry URIs to SQLite
    mlflow.set_tracking_uri(args.backend)
    mlflow.set_registry_uri(args.backend)

    mlflow.set_experiment("northstrike")

    onnx_model = onnx.load(args.onnx)
    model_sha = sha256(args.onnx)
    ts = time.strftime("%Y-%m-%d_%H%M%S")

    with mlflow.start_run(run_name=f"register_{args.name}_{ts}") as run:
        mlflow.set_tags(
            {
                "target": args.name,
                "sha256": model_sha,
                "src_path": os.path.abspath(args.onnx),
            }
        )
        # Log ONNX and auto-register under args.name
        mlflow_onnx.log_model(
            onnx_model=onnx_model,
            artifact_path="model",
            registered_model_name=args.name,
        )
        run_id = run.info.run_id

    client = MlflowClient()
    # Find the newest version tied to this run
    version = None
    for mv in sorted(
        client.search_model_versions(f"name='{args.name}'"),
        key=lambda m: int(m.version),
        reverse=True,
    ):
        if mv.run_id == run_id:
            version = mv.version
            break
    if version is None:
        print("ERROR: could not find a registered version for this run", file=sys.stderr)
        sys.exit(3)

    stage = args.stage
    alias = args.alias or stage.lower()

    # Try to set a stage (still supported); also set an alias for modern workflows
    try:
        client.transition_model_version_stage(name=args.name, version=version, stage=stage)
    except Exception:
        pass
    try:
        client.set_registered_model_alias(args.name, alias, int(version))
    except Exception:
        pass

    out = {
        "name": args.name,
        "version": version,
        "sha256": model_sha,
        "run_id": run_id,
        "stage": stage,
        "alias": alias,
        "backend": args.backend,
    }
    os.makedirs("artifacts/perf", exist_ok=True)
    with open("artifacts/perf/mlflow_register_summary.json", "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
