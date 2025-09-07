import mlflow
from mlflow.tracking import MlflowClient

BACKEND = "sqlite:///artifacts/mlflow/mlflow.db"
MODEL = "perception.depth"

def test_registry_has_depth_model():
    mlflow.set_tracking_uri(BACKEND)
    mlflow.set_registry_uri(BACKEND)
    c = MlflowClient()
    versions = c.search_model_versions(f"name='{MODEL}'")
    assert len(versions) >= 1

def test_registry_staging_or_alias():
    mlflow.set_tracking_uri(BACKEND)
    mlflow.set_registry_uri(BACKEND)
    c = MlflowClient()
    versions = c.search_model_versions(f"name='{MODEL}'")
    has_staging = any(getattr(v, "current_stage", None) == "Staging" for v in versions)
    try:
        mv = c.get_model_version_by_alias(MODEL, "staging")
        has_alias = mv is not None
    except Exception:
        has_alias = False
    assert has_staging or has_alias
