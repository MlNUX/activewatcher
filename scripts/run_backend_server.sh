#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

HOST="${ACTIVEWATCHER_HOST:-127.0.0.1}"
PORT="${ACTIVEWATCHER_PORT:-8712}"
DB_PATH="${ACTIVEWATCHER_DB_PATH:-$HOME/.local/share/activewatcher/events.sqlite3}"
LOG_LEVEL="${ACTIVEWATCHER_LOG_LEVEL:-info}"

if command -v activewatcher >/dev/null 2>&1; then
  exec activewatcher server --host "${HOST}" --port "${PORT}" --db-path "${DB_PATH}" --log-level "${LOG_LEVEL}"
fi

if [[ -x "${ROOT_DIR}/.venv/bin/python" ]]; then
  exec "${ROOT_DIR}/.venv/bin/python" -m activewatcher server \
    --host "${HOST}" \
    --port "${PORT}" \
    --db-path "${DB_PATH}" \
    --log-level "${LOG_LEVEL}"
fi

exec python -m activewatcher server --host "${HOST}" --port "${PORT}" --db-path "${DB_PATH}" --log-level "${LOG_LEVEL}"
