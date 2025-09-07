#!/usr/bin/env bash
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
CMD=${1:-start}; PORT=${PORT:-8000}; PID=/tmp/http${PORT}.pid
case "$CMD" in
 start)
  test -f "$PID" && kill "$(cat "$PID")" 2>/dev/null || true
  fuser -k ${PORT}/tcp 2>/dev/null || true
  nohup python3 -m http.server "$PORT" --bind 127.0.0.1 >/tmp/http${PORT}.log 2>&1 &
  echo $! > "$PID"; echo "Serving http://127.0.0.1:${PORT}"
  ;;
 stop) test -f "$PID" && kill "$(cat "$PID")" || echo "No server";;
 status) test -f "$PID" && ps -p "$(cat "$PID")" || echo "stopped";;
 log) tail -n 200 "/tmp/http${PORT}.log";;
 *) echo "Usage: $0 {start|stop|status|log}"; exit 2;;
esac
