#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

HOST="${ACTIVEWATCHER_HOST:-127.0.0.1}"
PORT="${ACTIVEWATCHER_PORT:-8712}"
DB_PATH="${ACTIVEWATCHER_DB_PATH:-$HOME/.local/share/activewatcher/events.sqlite3}"
LOG_LEVEL="${ACTIVEWATCHER_LOG_LEVEL:-info}"
SERVER_URL="${ACTIVEWATCHER_SERVER_URL:-http://${HOST}:${PORT}}"

FRONTEND_HOST="${ACTIVEWATCHER_FRONTEND_HOST:-127.0.0.1}"
FRONTEND_PORT="${ACTIVEWATCHER_FRONTEND_PORT:-5173}"

FRONTEND_DIR="${ROOT_DIR}/frontend"

if [[ ! -d "${FRONTEND_DIR}" ]]; then
  echo "[activewatcher] frontend directory missing: ${FRONTEND_DIR}" >&2
  exit 1
fi

if [[ ! -f "${FRONTEND_DIR}/package.json" ]]; then
  echo "[activewatcher] frontend package.json missing: ${FRONTEND_DIR}/package.json" >&2
  exit 1
fi

if ! command -v npm >/dev/null 2>&1; then
  echo "[activewatcher] npm not found. Install Node.js + npm first." >&2
  exit 1
fi

if command -v activewatcher >/dev/null 2>&1; then
  AW=(activewatcher)
else
  AW=(python -m activewatcher)
fi

echo "[activewatcher] backend: ${SERVER_URL}"
echo "[activewatcher] frontend: http://${FRONTEND_HOST}:${FRONTEND_PORT}"

if [[ ! -d "${FRONTEND_DIR}/node_modules" ]]; then
  echo "[activewatcher] installing frontend dependencies..."
  (cd "${FRONTEND_DIR}" && npm install)
fi

pids=()

cleanup() {
  for pid in "${pids[@]:-}"; do
    kill "$pid" >/dev/null 2>&1 || true
  done
}
trap cleanup EXIT INT TERM

echo "[activewatcher] starting backend..."
"${AW[@]}" server --host "${HOST}" --port "${PORT}" --db-path "${DB_PATH}" --log-level "${LOG_LEVEL}" &
pids+=("$!")

healthcheck() {
  if command -v curl >/dev/null 2>&1; then
    curl -sf "${SERVER_URL}/health" >/dev/null
  else
    python - <<PY >/dev/null
import urllib.request
urllib.request.urlopen("${SERVER_URL}/health", timeout=2).read()
PY
  fi
}

for _ in $(seq 1 60); do
  if healthcheck; then
    break
  fi
  sleep 0.1
done

if ! healthcheck; then
  echo "[activewatcher] backend healthcheck failed: ${SERVER_URL}/health" >&2
  exit 1
fi

echo "[activewatcher] starting frontend dev server..."
(cd "${FRONTEND_DIR}" && npm run dev -- --host "${FRONTEND_HOST}" --port "${FRONTEND_PORT}") &
pids+=("$!")

echo "[activewatcher] running (Ctrl-C to stop)"
wait -n "${pids[@]}"
exit 1
