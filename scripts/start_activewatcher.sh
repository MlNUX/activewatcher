#!/usr/bin/env bash
set -euo pipefail

HOST="${ACTIVEWATCHER_HOST:-127.0.0.1}"
PORT="${ACTIVEWATCHER_PORT:-8712}"
DB_PATH="${ACTIVEWATCHER_DB_PATH:-$HOME/.local/share/activewatcher/events.sqlite3}"
SERVER_URL="${ACTIVEWATCHER_SERVER_URL:-http://${HOST}:${PORT}}"
LOG_LEVEL="${ACTIVEWATCHER_LOG_LEVEL:-info}"

IDLE_THRESHOLD_SECONDS="${ACTIVEWATCHER_IDLE_THRESHOLD_SECONDS:-120}"

TRACK_FOCUSED="${ACTIVEWATCHER_TRACK_FOCUSED:-1}"
TRACK_VISIBLE_WINDOWS="${ACTIVEWATCHER_TRACK_VISIBLE_WINDOWS:-1}"
VISIBLE_ALL_MONITORS="${ACTIVEWATCHER_VISIBLE_ALL_MONITORS:-0}"
TRACK_OPEN_APPS="${ACTIVEWATCHER_TRACK_OPEN_APPS:-1}"
TRACK_WORKSPACES="${ACTIVEWATCHER_TRACK_WORKSPACES:-1}"

if command -v activewatcher >/dev/null 2>&1; then
  AW=(activewatcher)
else
  AW=(python -m activewatcher)
fi

echo "[activewatcher] server: ${SERVER_URL}"
echo "[activewatcher] db: ${DB_PATH}"

pids=()

cleanup() {
  for pid in "${pids[@]:-}"; do
    kill "$pid" >/dev/null 2>&1 || true
  done
}
trap cleanup EXIT INT TERM

"${AW[@]}" server --host "${HOST}" --port "${PORT}" --db-path "${DB_PATH}" --log-level "${LOG_LEVEL}" &
pids+=("$!")

healthcheck() {
  if command -v curl >/dev/null 2>&1; then
    curl -sf "${SERVER_URL}/health" >/dev/null
  else
    python - <<PY >/dev/null
import json, urllib.request
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

hypr_args=()
if [[ "${TRACK_FOCUSED}" == "1" ]]; then hypr_args+=(--track-focused); else hypr_args+=(--no-track-focused); fi
if [[ "${TRACK_VISIBLE_WINDOWS}" == "1" ]]; then hypr_args+=(--track-visible-windows); else hypr_args+=(--no-track-visible-windows); fi
if [[ "${VISIBLE_ALL_MONITORS}" == "1" ]]; then hypr_args+=(--visible-all-monitors); else hypr_args+=(--no-visible-all-monitors); fi
if [[ "${TRACK_OPEN_APPS}" == "1" ]]; then hypr_args+=(--track-open-apps); else hypr_args+=(--no-track-open-apps); fi
if [[ "${TRACK_WORKSPACES}" == "1" ]]; then hypr_args+=(--track-workspaces); else hypr_args+=(--no-track-workspaces); fi

echo "[activewatcher] starting hyprland watcher (${hypr_args[*]})"
"${AW[@]}" watch hyprland --server-url "${SERVER_URL}" "${hypr_args[@]}" &
pids+=("$!")

echo "[activewatcher] starting idle watcher (threshold=${IDLE_THRESHOLD_SECONDS}s)"
"${AW[@]}" watch idle --server-url "${SERVER_URL}" --threshold-seconds "${IDLE_THRESHOLD_SECONDS}" &
pids+=("$!")

echo "[activewatcher] running (Ctrl-C to stop)"
wait -n "${pids[@]}"
exit 1
