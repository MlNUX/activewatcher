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
```

Web UI:

- `http://127.0.0.1:8712/` (redirects to `/ui`)
- `http://127.0.0.1:8712/ui`
- `http://127.0.0.1:8712/ui/stats` (includes detailed logs)
- Includes a GitHub-style daily heatmap ("Calendar") with app filtering.

## Browser tabs (optional)

There is a small browser extension that reports open tab counts plus tab metadata
(URL/title/flags) to the server (`bucket=browser_tabs`). It supports Brave, Chrome, and Firefox.

Extension files live in `extensions/browser-tabs/`.

Load it as an unpacked extension:

- Chromium/Brave: `chrome://extensions` → enable "Developer mode" → "Load unpacked"
- Firefox: `about:debugging#/runtime/this-firefox` → "Load Temporary Add-on"

The charts appear on `/ui/stats` under "Browser Tabs" (count timeline, domain share, latest tabs).

## Hyprland autostart (exec-once)

Example snippet for `hyprland.conf`:

```ini
exec-once = activewatcher server --host 127.0.0.1 --port 8712
exec-once = activewatcher watch hyprland --server-url http://127.0.0.1:8712
exec-once = activewatcher watch idle --server-url http://127.0.0.1:8712 --threshold-seconds 120
```

## Config (env)

- `ACTIVEWATCHER_SERVER_URL` (default `http://127.0.0.1:8712`)
- `ACTIVEWATCHER_DB_PATH` (default `~/.local/share/activewatcher/events.sqlite3`)
- `ACTIVEWATCHER_STALE_AFTER_SECONDS` (default `120`): if a source stops sending updates for longer than this,
  open intervals are treated as ended at their `last_seen_ts` in summaries.
