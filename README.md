# activewatcher

Local activity tracker (Hyprland + Wayland) with a small FastAPI server + SQLite.

## Quickstart (dev)

If you don't want to install the package yet, you can run it directly from the repo root:
`python -m activewatcher --help`

```bash
python -m venv .venv
. .venv/bin/activate
pip install -U pip setuptools wheel
pip install -e . --no-build-isolation
```

Start server:

```bash
activewatcher server --host 127.0.0.1 --port 8712
```

Start watchers:

```bash
activewatcher watch hyprland --server-url http://127.0.0.1:8712
activewatcher watch idle --server-url http://127.0.0.1:8712 --threshold-seconds 120
activewatcher watch system --server-url http://127.0.0.1:8712 --poll-seconds 5.0
```

Notes:

- The `idle` watcher treats a locked session as AFK. By default, it also treats `hyprlock` running as "locked"
  (override with `--lock-process ""` or set a different process name).

Optional Hyprland tracking modes:

```bash
# Track all visible windows on the focused monitor (in addition to focused window)
activewatcher watch hyprland --server-url http://127.0.0.1:8712 --track-visible-windows

# Track visible windows across all monitors + track open apps
activewatcher watch hyprland --server-url http://127.0.0.1:8712 --track-visible-windows --visible-all-monitors --track-open-apps
```

Query:

```bash
activewatcher summary --server-url http://127.0.0.1:8712
activewatcher events --server-url http://127.0.0.1:8712 --bucket window
activewatcher events --server-url http://127.0.0.1:8712 --bucket window_visible
activewatcher events --server-url http://127.0.0.1:8712 --bucket app_open
activewatcher events --server-url http://127.0.0.1:8712 --bucket workspace
activewatcher events --server-url http://127.0.0.1:8712 --bucket workspace_switch
activewatcher events --server-url http://127.0.0.1:8712 --bucket system
```

Web UI:

- `http://127.0.0.1:8712/` (redirects to `/ui`)
- `http://127.0.0.1:8712/ui`
- `http://127.0.0.1:8712/ui/stats` (includes detailed logs)
- Includes a GitHub-style daily heatmap ("Calendar") with app filtering.

## Frontend (React + Vite)

There is now a separate frontend app in `frontend/` (React + TypeScript + Vite).

Development:

```bash
cd frontend
npm install
npm run dev
```

Start backend + frontend together:

```bash
./scripts/start_backend_frontend.sh
```

Always-on backend + desktop launcher:

```bash
./scripts/install_user_integration.sh
```

This installs:

- `~/.config/systemd/user/activewatcher-backend.service` (enabled + started)
- `~/.local/share/applications/activewatcher-frontend.desktop` (opens `/ui`)

Useful commands:

```bash
systemctl --user status activewatcher-backend.service
systemctl --user restart activewatcher-backend.service
systemctl --user disable --now activewatcher-backend.service
```

Build for FastAPI serving:

```bash
cd frontend
npm run build
```

Behavior:

- If `frontend/dist/index.html` exists, FastAPI serves the built React app on `/ui` and `/ui/stats`.
- If no frontend build exists, FastAPI returns `503` on `/ui*` with a build hint.
- You can override the dist folder via `ACTIVEWATCHER_WEB_DIST`.

## Browser tabs (optional)

There is a small browser extension that reports open tab counts plus tab metadata
(URL/title/flags) to the server (`bucket=browser_tabs`). It supports Brave, Chrome, and Firefox.

Extension files live in `extensions/browser-tabs/`.

Load it as an unpacked extension:

- Chromium/Brave: `chrome://extensions` → enable "Developer mode" → "Load unpacked"
- Firefox: `about:debugging#/runtime/this-firefox` → "Load Temporary Add-on"

The charts appear on `/ui/stats` under "Browser Tabs" (count timeline, domain share, latest tabs).

## App/Tab categories

`/ui/stats` includes a "Categories" widget that groups:

- Apps (active/window/visible mode)
- Browser tabs (tab-time by category)
- Default categories include `Coding`, `Communication`, `Uni`, `Research`, `Ops`, `Media`, `Social`, `Other`.

Rules are loaded from defaults, or from a JSON override file via:

- `ACTIVEWATCHER_CATEGORIES_PATH` (default `~/.local/share/activewatcher/categories.json`)

Example rule file:

- `activewatcher/config/categories.example.json`

API:

- `GET /v1/categories?from=...&to=...&mode=auto|active|window|visible`

## Hyprland autostart (exec-once)

Example snippet for `hyprland.conf`:

```ini
exec-once = activewatcher server --host 127.0.0.1 --port 8712
exec-once = activewatcher watch hyprland --server-url http://127.0.0.1:8712
exec-once = activewatcher watch idle --server-url http://127.0.0.1:8712 --threshold-seconds 120
exec-once = activewatcher watch system --server-url http://127.0.0.1:8712 --poll-seconds 5.0
```

## Tracking config (TOML)

You can control what gets tracked and at which interval via a config file:

- `ACTIVEWATCHER_CONFIG_PATH` (explicit file path), or
- default path: `~/.config/activewatcher/config.toml`

Example file:

- `activewatcher/config/watcher.example.toml`

Priority order:

- CLI options
- environment variables
- config file
- built-in defaults

`./scripts/start_backend_frontend.sh` uses the same config keys.

## Config (env)

- `ACTIVEWATCHER_CONFIG_PATH` (default `~/.config/activewatcher/config.toml`)
- `ACTIVEWATCHER_SERVER_URL` (default `http://127.0.0.1:8712`)
- `ACTIVEWATCHER_DB_PATH` (default `~/.local/share/activewatcher/events.sqlite3`)
- `ACTIVEWATCHER_CATEGORIES_PATH` (default `~/.local/share/activewatcher/categories.json`)
- `ACTIVEWATCHER_STALE_AFTER_SECONDS` (default `120`): if a source stops sending updates for longer than this,
  open intervals are treated as ended at their `last_seen_ts` in summaries.
- Watcher enable flags:
  - `ACTIVEWATCHER_TRACK_HYPRLAND`
  - `ACTIVEWATCHER_TRACK_IDLE`
  - `ACTIVEWATCHER_TRACK_SYSTEM`
- Key interval overrides:
  - `ACTIVEWATCHER_IDLE_POLL_SECONDS`
  - `ACTIVEWATCHER_SYSTEM_POLL_SECONDS`
  - `ACTIVEWATCHER_HYPRLAND_HEARTBEAT_SECONDS`
  - `ACTIVEWATCHER_IDLE_HEARTBEAT_SECONDS`
  - `ACTIVEWATCHER_SYSTEM_HEARTBEAT_SECONDS`
- Key Hyprland tracking toggles:
  - `ACTIVEWATCHER_TRACK_FOCUSED`
  - `ACTIVEWATCHER_TRACK_VISIBLE_WINDOWS`
  - `ACTIVEWATCHER_TRACK_OPEN_APPS`
  - `ACTIVEWATCHER_TRACK_WORKSPACES`
  - `ACTIVEWATCHER_VISIBLE_ALL_MONITORS`
