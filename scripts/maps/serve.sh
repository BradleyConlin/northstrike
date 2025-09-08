#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
PORT=8000
PIDFILE=.tmp/http.pid
mkdir -p .tmp

cmd=${1:-start}
if [[ "${cmd}" == "stop" ]]; then
  [[ -f "$PIDFILE" ]] && kill "$(cat "$PIDFILE")" 2>/dev/null || true
  rm -f "$PIDFILE"; echo "stopped"; exit 0
fi

[[ -f "$PIDFILE" ]] && kill "$(cat "$PIDFILE")" 2>/dev/null || true
rm -f "$PIDFILE"

python3 -m http.server "$PORT" --bind 127.0.0.1 >/dev/null 2>&1 &
echo $! > "$PIDFILE"
echo "started http://127.0.0.1:${PORT} (pid $(cat "$PIDFILE"))"
