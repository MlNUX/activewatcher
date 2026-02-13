#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SERVICE_NAME="activewatcher-backend.service"
DESKTOP_NAME="activewatcher-frontend.desktop"

XDG_CONFIG_HOME="${XDG_CONFIG_HOME:-$HOME/.config}"
XDG_DATA_HOME="${XDG_DATA_HOME:-$HOME/.local/share}"

SYSTEMD_USER_DIR="${XDG_CONFIG_HOME}/systemd/user"
APPLICATIONS_DIR="${XDG_DATA_HOME}/applications"

SERVICE_PATH="${SYSTEMD_USER_DIR}/${SERVICE_NAME}"
DESKTOP_PATH="${APPLICATIONS_DIR}/${DESKTOP_NAME}"

mkdir -p "${SYSTEMD_USER_DIR}" "${APPLICATIONS_DIR}"

cat > "${SERVICE_PATH}" <<EOF
[Unit]
Description=Activewatcher Backend
After=default.target

[Service]
Type=simple
WorkingDirectory=${ROOT_DIR}
ExecStart=${ROOT_DIR}/scripts/run_backend_server.sh
Restart=always
RestartSec=3

[Install]
WantedBy=default.target
EOF

cat > "${DESKTOP_PATH}" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Activewatcher Frontend
Comment=Open Activewatcher Web UI
Exec=xdg-open http://127.0.0.1:8712/ui
Terminal=false
Categories=Utility;
Icon=utilities-system-monitor
StartupNotify=false
EOF

if command -v systemctl >/dev/null 2>&1; then
  systemctl --user daemon-reload
  systemctl --user enable --now "${SERVICE_NAME}"
else
  echo "[activewatcher] warning: systemctl not found, service file created but not enabled" >&2
fi

chmod +x "${ROOT_DIR}/scripts/run_backend_server.sh"
chmod 0644 "${SERVICE_PATH}" "${DESKTOP_PATH}"

echo "[activewatcher] installed service: ${SERVICE_PATH}"
echo "[activewatcher] installed desktop entry: ${DESKTOP_PATH}"
echo "[activewatcher] frontend launcher opens: http://127.0.0.1:8712/ui"
