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

load_tracking_defaults() {
  TRACK_HYPRLAND=1
  TRACK_IDLE=1
  TRACK_SYSTEM=1
  TRACK_BATTERY=1

  TRACK_FOCUSED=1
  TRACK_VISIBLE_WINDOWS=1
  VISIBLE_ALL_MONITORS=0
  TRACK_OPEN_APPS=1
  TRACK_WORKSPACES=1
  HYPRLAND_DEBOUNCE_MS=120
  HYPRLAND_TITLE_MAX_LEN=200
  HYPRLAND_HEARTBEAT_SECONDS=30

  IDLE_THRESHOLD_SECONDS=120
  IDLE_POLL_SECONDS=5.0
  IDLE_HEARTBEAT_SECONDS=30
  IDLE_LOCK_PROCESS="hyprlock"

  SYSTEM_POLL_SECONDS=5.0
  SYSTEM_HEARTBEAT_SECONDS=30
  SYSTEM_INCLUDE_LOOPBACK=0

  BATTERY_POLL_SECONDS=15.0
  BATTERY_HEARTBEAT_SECONDS=60

  if ! command -v python >/dev/null 2>&1; then
    return
  fi

  local py_out
  if ! py_out="$(
    PYTHONPATH="${ROOT_DIR}${PYTHONPATH:+:${PYTHONPATH}}" python - <<'PY'
from __future__ import annotations

import shlex

from activewatcher.common import config as cfg


def b(value: bool) -> str:
    return "1" if value else "0"


values: dict[str, str] = {
    "TRACK_HYPRLAND": b(
        cfg.config_bool(("watch", "hyprland", "enabled"), env_var="ACTIVEWATCHER_TRACK_HYPRLAND", default=True)
    ),
    "TRACK_IDLE": b(cfg.config_bool(("watch", "idle", "enabled"), env_var="ACTIVEWATCHER_TRACK_IDLE", default=True)),
    "TRACK_SYSTEM": b(
        cfg.config_bool(("watch", "system", "enabled"), env_var="ACTIVEWATCHER_TRACK_SYSTEM", default=True)
    ),
    "TRACK_BATTERY": b(
        cfg.config_bool(("watch", "battery", "enabled"), env_var="ACTIVEWATCHER_TRACK_BATTERY", default=True)
    ),
    "TRACK_FOCUSED": b(
        cfg.config_bool(("watch", "hyprland", "track_focused"), env_var="ACTIVEWATCHER_TRACK_FOCUSED", default=True)
    ),
    "TRACK_VISIBLE_WINDOWS": b(
        cfg.config_bool(
            ("watch", "hyprland", "track_visible_windows"),
            env_var="ACTIVEWATCHER_TRACK_VISIBLE_WINDOWS",
            default=True,
        )
    ),
    "VISIBLE_ALL_MONITORS": b(
        cfg.config_bool(
            ("watch", "hyprland", "visible_all_monitors"),
            env_var="ACTIVEWATCHER_VISIBLE_ALL_MONITORS",
            default=False,
        )
    ),
    "TRACK_OPEN_APPS": b(
        cfg.config_bool(("watch", "hyprland", "track_open_apps"), env_var="ACTIVEWATCHER_TRACK_OPEN_APPS", default=True)
    ),
    "TRACK_WORKSPACES": b(
        cfg.config_bool(("watch", "hyprland", "track_workspaces"), env_var="ACTIVEWATCHER_TRACK_WORKSPACES", default=True)
    ),
    "HYPRLAND_DEBOUNCE_MS": str(
        cfg.config_int(("watch", "hyprland", "debounce_ms"), env_var="ACTIVEWATCHER_HYPRLAND_DEBOUNCE_MS", default=120)
    ),
    "HYPRLAND_TITLE_MAX_LEN": str(
        cfg.config_int(("watch", "hyprland", "title_max_len"), env_var="ACTIVEWATCHER_HYPRLAND_TITLE_MAX_LEN", default=200)
    ),
    "HYPRLAND_HEARTBEAT_SECONDS": str(
        cfg.config_int(
            ("watch", "hyprland", "heartbeat_seconds"),
            env_var="ACTIVEWATCHER_HYPRLAND_HEARTBEAT_SECONDS",
            default=30,
        )
    ),
    "IDLE_THRESHOLD_SECONDS": str(
        cfg.config_int(
            ("watch", "idle", "threshold_seconds"),
            env_var="ACTIVEWATCHER_IDLE_THRESHOLD_SECONDS",
            default=120,
        )
    ),
    "IDLE_POLL_SECONDS": str(
        cfg.config_float(("watch", "idle", "poll_seconds"), env_var="ACTIVEWATCHER_IDLE_POLL_SECONDS", default=5.0)
    ),
    "IDLE_HEARTBEAT_SECONDS": str(
        cfg.config_int(
            ("watch", "idle", "heartbeat_seconds"), env_var="ACTIVEWATCHER_IDLE_HEARTBEAT_SECONDS", default=30
        )
    ),
    "IDLE_LOCK_PROCESS": cfg.config_str(
        ("watch", "idle", "lock_process"),
        env_var="ACTIVEWATCHER_IDLE_LOCK_PROCESS",
        default="hyprlock",
        allow_empty=True,
    ),
    "SYSTEM_POLL_SECONDS": str(
        cfg.config_float(("watch", "system", "poll_seconds"), env_var="ACTIVEWATCHER_SYSTEM_POLL_SECONDS", default=5.0)
    ),
    "SYSTEM_HEARTBEAT_SECONDS": str(
        cfg.config_int(
            ("watch", "system", "heartbeat_seconds"), env_var="ACTIVEWATCHER_SYSTEM_HEARTBEAT_SECONDS", default=30
        )
    ),
    "SYSTEM_INCLUDE_LOOPBACK": b(
        cfg.config_bool(
            ("watch", "system", "include_loopback"), env_var="ACTIVEWATCHER_SYSTEM_INCLUDE_LOOPBACK", default=False
        )
    ),
    "BATTERY_POLL_SECONDS": str(
        cfg.config_float(("watch", "battery", "poll_seconds"), env_var="ACTIVEWATCHER_BATTERY_POLL_SECONDS", default=15.0)
    ),
    "BATTERY_HEARTBEAT_SECONDS": str(
        cfg.config_int(
            ("watch", "battery", "heartbeat_seconds"),
            env_var="ACTIVEWATCHER_BATTERY_HEARTBEAT_SECONDS",
            default=60,
        )
    ),
}

for key, value in values.items():
    print(f"{key}={shlex.quote(value)}")
PY
  )"; then
    echo "[activewatcher] failed to load config file, using built-in defaults" >&2
    return
  fi

  eval "${py_out}"
}

load_tracking_defaults

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
echo "[activewatcher] db: ${DB_PATH}"
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

hypr_args=(
  --debounce-ms "${HYPRLAND_DEBOUNCE_MS}"
  --title-max-len "${HYPRLAND_TITLE_MAX_LEN}"
  --heartbeat-seconds "${HYPRLAND_HEARTBEAT_SECONDS}"
)
if [[ "${TRACK_FOCUSED}" == "1" ]]; then hypr_args+=(--track-focused); else hypr_args+=(--no-track-focused); fi
if [[ "${TRACK_VISIBLE_WINDOWS}" == "1" ]]; then hypr_args+=(--track-visible-windows); else hypr_args+=(--no-track-visible-windows); fi
if [[ "${VISIBLE_ALL_MONITORS}" == "1" ]]; then hypr_args+=(--visible-all-monitors); else hypr_args+=(--no-visible-all-monitors); fi
if [[ "${TRACK_OPEN_APPS}" == "1" ]]; then hypr_args+=(--track-open-apps); else hypr_args+=(--no-track-open-apps); fi
if [[ "${TRACK_WORKSPACES}" == "1" ]]; then hypr_args+=(--track-workspaces); else hypr_args+=(--no-track-workspaces); fi

if [[ "${TRACK_HYPRLAND}" == "1" ]]; then
  echo "[activewatcher] starting hyprland watcher (${hypr_args[*]})"
  "${AW[@]}" watch hyprland --server-url "${SERVER_URL}" "${hypr_args[@]}" &
  pids+=("$!")
else
  echo "[activewatcher] skipping hyprland watcher (disabled)"
fi

if [[ "${TRACK_IDLE}" == "1" ]]; then
  echo "[activewatcher] starting idle watcher (threshold=${IDLE_THRESHOLD_SECONDS}s poll=${IDLE_POLL_SECONDS}s)"
  "${AW[@]}" watch idle \
    --server-url "${SERVER_URL}" \
    --threshold-seconds "${IDLE_THRESHOLD_SECONDS}" \
    --poll-seconds "${IDLE_POLL_SECONDS}" \
    --heartbeat-seconds "${IDLE_HEARTBEAT_SECONDS}" \
    --lock-process "${IDLE_LOCK_PROCESS}" &
  pids+=("$!")
else
  echo "[activewatcher] skipping idle watcher (disabled)"
fi

if [[ "${TRACK_SYSTEM}" == "1" ]]; then
  system_args=(--poll-seconds "${SYSTEM_POLL_SECONDS}" --heartbeat-seconds "${SYSTEM_HEARTBEAT_SECONDS}")
  if [[ "${SYSTEM_INCLUDE_LOOPBACK}" == "1" ]]; then
    system_args+=(--include-loopback)
  else
    system_args+=(--no-include-loopback)
  fi
  echo "[activewatcher] starting system watcher (poll=${SYSTEM_POLL_SECONDS}s)"
  "${AW[@]}" watch system --server-url "${SERVER_URL}" "${system_args[@]}" &
  pids+=("$!")
fi

if [[ "${TRACK_BATTERY}" == "1" ]]; then
  echo "[activewatcher] starting battery watcher (poll=${BATTERY_POLL_SECONDS}s)"
  "${AW[@]}" watch battery \
    --server-url "${SERVER_URL}" \
    --poll-seconds "${BATTERY_POLL_SECONDS}" \
    --heartbeat-seconds "${BATTERY_HEARTBEAT_SECONDS}" &
  pids+=("$!")
else
  echo "[activewatcher] skipping battery watcher (disabled)"
fi

echo "[activewatcher] starting frontend dev server..."
(cd "${FRONTEND_DIR}" && npm run dev -- --host "${FRONTEND_HOST}" --port "${FRONTEND_PORT}") &
pids+=("$!")

echo "[activewatcher] running (Ctrl-C to stop)"
wait -n "${pids[@]}"
exit 1
