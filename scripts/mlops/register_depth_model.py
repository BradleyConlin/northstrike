#!/usr/bin/env python3
import argparse, hashlib, json, os, sys, time
import onnx
import mlflow
from mlflow.tracking import MlflowClient

def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="perception.depth")
    ap.add_argument("--onnx", default="artifacts/onnx/depth_e24.onnx")
    ap.add_argument("--backend", default="sqlite:///artifacts/mlflow/mlflow.db")
    ap.add_argument("--artifact-root", default="file:mlruns")
    ap.add_argument("--stage", default="Staging")  # Staging|Production|None
    args = ap.parse_args()

    if not os.path.exists(args.onnx):
        print(f"ERROR: missing ONNX at {args.onnx}", file=sys.stderr)
        sys.exit(2)

    # Point MLflow to SQLite backend (registry requires DB store).
    # UI later: mlflow ui --backend-store-uri sqlite:///artifacts/mlflow/mlflow.db --port 5001
    mlflow.set_tracking_uri(args.backend)
    mlflow.set_registry_uri(args.backend)  # DB-backed store for registry
    mlflow.set_experiment("northstrike")

    onnx_model = onnx.load(args.onnx)
    model_sha = sha256(args.onnx)
    ts = time.strftime("%Y-%m-%d_%H%M%S")

    with mlflow.start_run(run_name=f"register_{args.name}_{ts}") as run:
        mlflow.set_tags({
            "target": args.name,
            "sha256": model_sha,
            "src_path": os.path.abspath(args.onnx),
        })
        # Log ONNX as an MLflow Model and auto-register it
from mlflow import onnx as mlflow_onnx
        logged = mlflow_onnx.log_model(
            onnx_model=onnx_model,
            artifact_path="model",
            registered_model_name=args.name,
        )
        run_id = run.info.run_id

    # Grab latest model version that corresponds to this run
    client = MlflowClient()
    vers = client.search_model_versions(f"name='{args.name}'")
    # pick the newest version for this run_id
    for mv in sorted(vers, key=lambda m: int(m.version), reverse=True):
        if mv.run_id == run_id:
            version = mv.version
            break
    else:
        print("ERROR: could not find a registered version for this run", file=sys.stderr)
        sys.exit(3)

    # Try to set a stage (note: stages are being deprecated in newer MLflow; aliases are replacing them)
    # We'll set stage if supported; otherwise we set an alias 'staging'.
    try:
        client.transition_model_version_stage(name=args.name, version=version, stage=args.stage)
    except Exception as e:
        # Fallback: set alias (e.g., 'staging') if stages aren't enabled
        alias = args.stage.lower()
        try:
            client.set_registered_model_alias(args.name, alias, int(version))
        except Exception:
            print(f"Stage/alias not set: {e}", file=sys.stderr)

    # Nice summary JSON
    out = {
        "name": args.name,
        "version": version,
        "sha256": model_sha,
        "run_id": run_id,
        "stage_or_alias": args.stage,
        "backend": args.backend,
    }
    os.makedirs("artifacts/perf", exist_ok=True)
    with open("artifacts/perf/mlflow_register_summary.json", "w") as f:
        json.dump(out, f, indent=2)
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()
