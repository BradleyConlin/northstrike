#!/usr/bin/env python3
import argparse, mlflow
from mlflow.tracking import MlflowClient

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--alias", required=True)  # e.g., production, staging
    ap.add_argument("--version", type=int, default=None)
    ap.add_argument("--backend", default="sqlite:///artifacts/mlflow/mlflow.db")
    args = ap.parse_args()

    mlflow.set_tracking_uri(args.backend)
    mlflow.set_registry_uri(args.backend)
    c = MlflowClient()

    v = args.version
    if v is None:
        mv = sorted(c.search_model_versions(f"name='{args.name}'"),
                    key=lambda m: int(m.version), reverse=True)[0]
        v = int(mv.version)
    c.set_registered_model_alias(args.name, args.alias, v)
    print(f"Alias {args.alias} -> {args.name} v{v}")

if __name__ == "__main__":
    main()
