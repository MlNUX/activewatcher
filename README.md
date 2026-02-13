# activewatcher

Local activity tracker for Linux/Wayland (focused on Hyprland):

- FastAPI backend + SQLite
- Watchers for window activity, idle/AFK, system metrics, and battery state
- React dashboard for analysis
- Optional browser extension for tab metrics

Everything runs locally on your machine.

## What Runs Here (and Why)

`activewatcher` uses a local API process as its backend. This is intentional.

- The backend process is a local HTTP server (`127.0.0.1:8712`) that writes/reads SQLite data.
- Watchers run as separate processes and send events to `POST /v1/state`.
- CLI reports and the dashboard read data from the same API (`/v1/summary`, `/v1/events`, etc.).

So "backend starts a server" means "backend starts the local API service used by all components." It is not a cloud service.

## Table of Contents

- [Requirements](#requirements)
- [Quick Start (Recommended)](#quick-start-recommended)
- [Low-Resource Mode (No Frontend Process)](#low-resource-mode-no-frontend-process)
- [Frontend (React + Vite)](#frontend-react--vite)
- [Browser Tabs (Optional)](#browser-tabs-optional)
- [Categories (Apps and Tabs)](#categories-apps-and-tabs)
- [Configuration](#configuration)
- [Autostart](#autostart)
- [API and CLI Quick Reference](#api-and-cli-quick-reference)
- [Troubleshooting](#troubleshooting)

## Requirements

- Linux (Wayland; Hyprland session required for the Hyprland watcher)
- Python `>= 3.11`
- Node.js + npm (only needed for frontend development/build)

## Quick Start (Recommended)

From the repo root:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -U pip setuptools wheel
pip install -e . --no-build-isolation
./scripts/start_backend_frontend.sh
```

This starts:

- Backend API: `http://127.0.0.1:8712`
- Watchers: `hyprland`, `idle`, `system`, `battery`
- Vite dev frontend: `http://127.0.0.1:5173`

Quick checks:

- `http://127.0.0.1:8712/health`
- `http://127.0.0.1:8712/docs`
- `http://127.0.0.1:5173`

Note: `start_backend_frontend.sh` enables richer Hyprland tracking by default (including visible windows and open apps).

## Low-Resource Mode (No Frontend Process)

If you want lower resource usage, do not run the Vite dev server and do not keep the dashboard open.

Start only backend + watchers:

```bash
activewatcher server --host 127.0.0.1 --port 8712
```

In separate terminals:

```bash
activewatcher watch hyprland --server-url http://127.0.0.1:8712
activewatcher watch idle --server-url http://127.0.0.1:8712 --threshold-seconds 120
activewatcher watch system --server-url http://127.0.0.1:8712 --poll-seconds 5.0
activewatcher watch battery --server-url http://127.0.0.1:8712 --poll-seconds 15.0
```

Performance notes:

- The backend API itself is usually lightweight.
- Extra load mainly comes from:
  - running `npm run dev` (Vite process)
  - keeping `/ui` open (the dashboard refreshes data periodically)

## Frontend (React + Vite)

Frontend source is in `frontend/`.

Development:

```bash
cd frontend
npm install
npm run dev
```

Build for backend serving:

```bash
cd frontend
npm run build
```

Backend behavior:

- If `frontend/dist/index.html` exists, FastAPI serves the UI on `/ui` and `/ui/stats`.
- If no build exists, `/ui*` returns `503` with a build hint.
- You can override the dist directory with `ACTIVEWATCHER_WEB_DIST`.

## Browser Tabs (Optional)

Extension files are in `extensions/browser-tabs/`.

The extension sends tab count and tab metadata (`url`, `title`, flags) to the backend as `bucket=browser_tabs`.

Supported browsers: Brave, Chrome, Firefox.

Load as unpacked extension:

- Chromium/Brave: `chrome://extensions` -> enable Developer mode -> Load unpacked
- Firefox: `about:debugging#/runtime/this-firefox` -> Load Temporary Add-on

Charts appear in `/ui/stats` under "Browser Tabs".

## Categories (Apps and Tabs)

`/ui/stats` includes category summaries for:

- app time (mode-dependent)
- browser tab time

Category rules come from defaults or from a JSON override file:

- `ACTIVEWATCHER_CATEGORIES_PATH` (default: `~/.local/share/activewatcher/categories.json`)
- example: `activewatcher/config/categories.example.json`

API:

- `GET /v1/categories?from=...&to=...&mode=auto|active|window|visible`

## Configuration

Config file:

- default path: `~/.config/activewatcher/config.toml`
- explicit override: `ACTIVEWATCHER_CONFIG_PATH=/path/to/config.toml`
- template: `activewatcher/config/watcher.example.toml`

Quick setup:

```bash
mkdir -p ~/.config/activewatcher
cp activewatcher/config/watcher.example.toml ~/.config/activewatcher/config.toml
```

Precedence:

1. CLI flags
2. environment variables
3. `config.toml`
4. built-in defaults

Important environment variables:

- `ACTIVEWATCHER_SERVER_URL` (default `http://127.0.0.1:8712`)
- `ACTIVEWATCHER_DB_PATH` (default `~/.local/share/activewatcher/events.sqlite3`)
- `ACTIVEWATCHER_CATEGORIES_PATH` (default `~/.local/share/activewatcher/categories.json`)
- `ACTIVEWATCHER_STALE_AFTER_SECONDS` (default `120`)
- `ACTIVEWATCHER_TRACK_HYPRLAND`, `ACTIVEWATCHER_TRACK_IDLE`, `ACTIVEWATCHER_TRACK_SYSTEM`, `ACTIVEWATCHER_TRACK_BATTERY`
- `ACTIVEWATCHER_TRACK_FOCUSED`, `ACTIVEWATCHER_TRACK_VISIBLE_WINDOWS`, `ACTIVEWATCHER_TRACK_OPEN_APPS`
- `ACTIVEWATCHER_TRACK_WORKSPACES`, `ACTIVEWATCHER_VISIBLE_ALL_MONITORS`
- `ACTIVEWATCHER_IDLE_POLL_SECONDS`, `ACTIVEWATCHER_SYSTEM_POLL_SECONDS`, `ACTIVEWATCHER_BATTERY_POLL_SECONDS`
- `ACTIVEWATCHER_HYPRLAND_HEARTBEAT_SECONDS`, `ACTIVEWATCHER_IDLE_HEARTBEAT_SECONDS`, `ACTIVEWATCHER_SYSTEM_HEARTBEAT_SECONDS`, `ACTIVEWATCHER_BATTERY_HEARTBEAT_SECONDS`

Variables used by `scripts/start_backend_frontend.sh`:

- `ACTIVEWATCHER_HOST`, `ACTIVEWATCHER_PORT`
- `ACTIVEWATCHER_FRONTEND_HOST`, `ACTIVEWATCHER_FRONTEND_PORT`
- `ACTIVEWATCHER_LOG_LEVEL`

## Autostart

Use `~/.config/hypr/autostart.conf` as the startup method.

`exec-once` (full stack):

```ini
exec-once = $HOME/<path-to-activewatcher>/.venv/bin/activewatcher server --host 127.0.0.1 --port 8712
exec-once = $HOME/<path-to-activewatcher>/.venv/bin/activewatcher watch hyprland --server-url http://127.0.0.1:8712
exec-once = $HOME/<path-to-activewatcher>/.venv/bin/activewatcher watch idle --server-url http://127.0.0.1:8712 --threshold-seconds 120
exec-once = $HOME/<path-to-activewatcher>/.venv/bin/activewatcher watch system --server-url http://127.0.0.1:8712 --poll-seconds 5.0
exec-once = $HOME/<path-to-activewatcher>/.venv/bin/activewatcher watch battery --server-url http://127.0.0.1:8712 --poll-seconds 15.0
```

## API and CLI Quick Reference

Core routes:

- `GET /health`
- `GET /docs`
- `POST /v1/state`
- `GET /v1/events`
- `GET /v1/summary`
- `GET /v1/apps`
- `GET /v1/heatmap`
- `GET /v1/categories`
- `GET /v1/range`

CLI help:

```bash
python -m activewatcher --help
activewatcher --help
activewatcher watch --help
```

Useful queries:

```bash
activewatcher summary --server-url http://127.0.0.1:8712
activewatcher events --server-url http://127.0.0.1:8712 --bucket window
activewatcher events --server-url http://127.0.0.1:8712 --bucket window_visible
activewatcher events --server-url http://127.0.0.1:8712 --bucket app_open
activewatcher events --server-url http://127.0.0.1:8712 --bucket workspace
activewatcher events --server-url http://127.0.0.1:8712 --bucket workspace_switch
activewatcher events --server-url http://127.0.0.1:8712 --bucket system
activewatcher events --server-url http://127.0.0.1:8712 --bucket battery
```

## Troubleshooting

- `/ui` returns `503`: frontend build missing -> `cd frontend && npm run build`
- Hyprland watcher cannot find socket: start it inside an active Hyprland session
- No data in UI: verify watcher processes are running and `/health` is reachable
- Idle lock detection should not use `hyprlock`: set `--lock-process ""`
