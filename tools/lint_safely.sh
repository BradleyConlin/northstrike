#!/usr/bin/env bash
set -Eeuo pipefail
cd "${REPO:-$(pwd)}"

# Pick a Python (prefer .venv if present)
if [[ -x .venv/bin/python ]]; then PY=.venv/bin/python
elif command -v python3 >/dev/null 2>&1; then PY=$(command -v python3)
else PY=$(command -v python); fi

# Ensure required packages are present in that Python
"$PY" - <<'PY'
import importlib.util, subprocess, sys
pkgs = ["ruff","black","isort"]
need = [p for p in pkgs if importlib.util.find_spec(p) is None]
if need:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", *need])
PY

# Don’t let pre-commit re-run the same formatters during auto-commits
export SKIP="ruff-lint,ruff-format,black,isort,flake8-perception"

# Build list of tracked Python files, skipping heavy/noisy dirs
git ls-files -z '*.py' \
 | grep -z -v -E '^(datasets|training/runs|mlruns|logs|tmp|artifacts|build|dist|\.venv|sim/scripts/_archive)/' \
 > .lint_files.zlist

# Tiny cleanup to fix the odd leading "/" import lines you had
sed -E -i 's|^([[:space:]]*)/[[:space:]]*import[[:space:]]+|\1import |; s|^([[:space:]]*)/[[:space:]]*from[[:space:]]+|\1from |' sim/rl/*.py 2>/dev/null || true

# Process files one-by-one; commit in batches so progress is saved
i=0
while IFS= read -r -d '' f; do
  i=$((i+1))
  "$PY" -m ruff format --force-exclude --stdin-filename "$f" < "$f" >/dev/null 2>&1 || true
  "$PY" -m black -q "$f" || true
  "$PY" -m isort -q "$f" || true
  # Safe fixes only; change to --unsafe-fixes after you see this pass
  "$PY" -m ruff check --select E,F,I,UP,B --fix --threads 1 --force-exclude -q "$f" || true
  (( i % 50 == 0 )) && { git add -A; git commit -m "chore(lint): ${i} files" || true; }
done < .lint_files.zlist

git add -A
git commit -m "chore(lint): final batch" || true
echo "✅ Lint/format complete."
