#!/usr/bin/env bash
set -euo pipefail

REPO="${REPO:-BradleyConlin/northstrike}"
BRANCH="${BRANCH:-main}"

watch_one() {
  local wf="$1"
  local id
  id="$(gh run list --repo "$REPO" --workflow "$wf" --branch "$BRANCH" -L 1 --json databaseId --jq '.[0].databaseId' 2>/dev/null || true)"
  if [[ -z "${id:-}" || "$id" == "null" ]]; then
    echo "No run found for '$wf' on '$BRANCH'." >&2
    return 1
  fi
  gh run watch --repo "$REPO" "$id" --exit-status || gh run view --repo "$REPO" "$id" --log-failed
}

if [[ $# -eq 0 ]]; then
  # Default set you care about; tweak order anytime
  for wf in datasets-verify maps-smoke ci-smoke onnx-gates; do
    watch_one "$wf" || true
  done
else
  for wf in "$@"; do
    watch_one "$wf" || true
  done
fi
