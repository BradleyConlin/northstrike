# Northstrike Monorepo (Source of Truth)

**Repo:** github.com/BradleyConlin/northstrike

## Layout
- `sim/` – linux sim (subtree of northstrike-linux-sim)
- `training/` – ML tooling (subtree of northstrike-training)
- `docs/` – SOPs & design notes
- `.github/workflows/` – CI pipelines
- `pyproject.toml` – Black/Ruff/isort/Pytest config
- `.pre-commit-config.yaml` – local hooks
- `.gitattributes` – LFS for .onnx/.pt/videos
- `.gitignore` – ignore venvs, datasets, runs, logs

## Standards
- Python 3.10; Black line-length 100; Ruff lint (E,F,I,UP,B).
- Hooks required: `pre-commit install` (run on every commit).
- CI must pass on PRs; datasets live outside repo.
- Grow lint scope from `training/` → `sim/` after we clean legacy files.

## Quickstart
```bash
git clone git@github.com:BradleyConlin/northstrike.git
cd northstrike && python3 -m venv .venv && . .venv/bin/activate
pip install -U pip && pip install pre-commit
pre-commit install
make lint || true
make test || true
