#!/usr/bin/env bash
set -euo pipefail
MODEL="${1:-}"; shift || true
[[ -n "${MODEL}" ]] || { echo "Usage: $0 path/to/model.onnx [extra trtexec args]"; exit 2; }
command -v trtexec >/dev/null 2>&1 || { echo "ERROR: trtexec not found"; exit 3; }

# Defaults: 200 runs, enable fp16 if supported; pass through extra args
EXTRA_ARGS=("$@")
OUTDIR="artifacts/perf"; mkdir -p "$OUTDIR"
STEM="$(basename "${MODEL%.*}")"
LOG="${OUTDIR}/trtexec_${STEM}.log"
JSON="${OUTDIR}/trtexec_${STEM}.json"

set +e
trtexec --onnx="${MODEL}" --fp16 --warmUp=10 --duration=15 --iterations=200 --avgRuns=10 \
        --noDataTransfers --timeout=0 "${EXTRA_ARGS[@]}" 2>&1 | tee "$LOG"
RC=$?
set -e

# Extract a number (ms) from typical outputs: "mean: X ms" or "Average over ... is X ms"
LAT=$(grep -Eo 'mean: *[0-9.]+ *ms' "$LOG" | tail -n1 | grep -Eo '[0-9.]+' || true)
[[ -z "$LAT" ]] && LAT=$(grep -Eo 'Average over .* is *[0-9.]+ *ms' "$LOG" | grep -Eo '[0-9.]+' | tail -n1 || true)
[[ -z "$LAT" ]] && LAT="NaN"

printf '{\n  "model": "%s",\n  "avg_latency_ms": %s,\n  "log": "%s",\n  "exit_code": %d\n}\n' \
  "$MODEL" "$LAT" "$LOG" "$RC" > "$JSON"
echo "Wrote $JSON"
exit $RC
