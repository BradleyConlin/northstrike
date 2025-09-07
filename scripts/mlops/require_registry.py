#!/usr/bin/env python3
import argparse, json, sys, os
import mlflow
from mlflow.tracking import MlflowClient

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", required=True)
    ap.add_argument("--backend", default="sqlite:///artifacts/mlflow/mlflow.db")
    ap.add_argument("--expect-alias", default=None)
    ap.add_argument("--expect-stage", default=None)   # e.g., Staging|Production
    ap.add_argument("--json-out", default=None)
    args = ap.parse_args()

    mlflow.set_tracking_uri(args.backend)
    mlflow.set_registry_uri(args.backend)
    c = MlflowClient()

    ok = True
    summary = {"name": args.name, "backend": args.backend, "checks": {}, "versions": []}

    # enumerate versions
    versions = sorted(
        c.search_model_versions(f"name='{args.name}'"),
        key=lambda m: int(m.version),
    )
    summary["versions"] = [
        {"version": int(m.version), "stage": getattr(m, "current_stage", None)}
        for m in versions
    ]
    summary["checks"]["has_any_version"] = bool(versions)
    ok &= bool(versions)

    # check alias if requested (MLflow 2.4+)
    if args.expect_alias:
        try:
            mv = c.get_model_version_by_alias(args.name, args.expect_alias)
            summary["checks"]["has_alias"] = True
            summary["alias_version"] = int(mv.version)
        except Exception:
            summary["checks"]["has_alias"] = False
            ok = False

    # check stage if requested
    if args.expect_stage:
        staged = [m for m in versions if getattr(m, "current_stage", None) == args.expect_stage]
        summary["checks"]["has_stage"] = bool(staged)
        if staged:
            summary["stage_versions"] = [int(m.version) for m in staged]
        ok &= bool(staged)

    if args.json_out:
        os.makedirs(os.path.dirname(args.json_out), exist_ok=True)
        with open(args.json_out, "w") as f:
            json.dump(summary, f, indent=2)
    print(json.dumps(summary, indent=2))
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
