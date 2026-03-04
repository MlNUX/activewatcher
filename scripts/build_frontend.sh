#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
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

echo "[activewatcher] installing frontend dependencies with npm ci..."
(cd "${FRONTEND_DIR}" && npm ci)

echo "[activewatcher] building frontend..."
(cd "${FRONTEND_DIR}" && npm run build)

echo "[activewatcher] frontend build finished"
