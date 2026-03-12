# activewatcher

Local activity tracker for Linux/Wayland (Hyprland-focused).  
Runs locally on `http://127.0.0.1:8712`.

## Requirements

- Linux + Wayland (Hyprland for `watch hyprland`)
- Python `>= 3.11`
- Node.js + npm

Install/update and build via Makefile:

```bash
make build
```

`make build` creates `.venv` if needed, updates pip tooling, installs the package in editable mode, then runs `npm ci` and `npm run build` for the frontend.

Useful targets:

- `make pip-update` updates `pip`, `setuptools`, and `wheel` in `.venv`.
- `make pip-build` installs the project in editable mode.
- `make frontend-build` runs `npm ci` and `npm run build` in `frontend/`.

## Security Defaults

- API CORS is restricted to local origins by default (`127.0.0.1`/`localhost` on ports `5173`, `5174`, `8712`).
- Host header checks are restricted to local hosts by default (`127.0.0.1`, `localhost`, `[::1]`).
- Optional write auth token for mutating endpoints (`POST /v1/state`, timers, autotag approve):
  - `server.write_token` or `ACTIVEWATCHER_WRITE_TOKEN`
  - clients send `X-ActiveWatcher-Token: <token>` (or `Authorization: Bearer <token>`)
- If no write token is configured, mutating endpoints still accept only local loopback clients.
- Override with config/env if needed:
  - `server.cors_origins` or `ACTIVEWATCHER_CORS_ORIGINS` (comma-separated)
  - `server.trusted_hosts` or `ACTIVEWATCHER_TRUSTED_HOSTS` (comma-separated)

## Autostart

In `~/.config/hypr/autostart.conf`:

```ini
exec-once = $HOME/<path-to-activewatcher>/.venv/bin/activewatcher server --host 127.0.0.1 --port 8712
exec-once = $HOME/<path-to-activewatcher>/.venv/bin/activewatcher watch hyprland --server-url http://127.0.0.1:8712
exec-once = $HOME/<path-to-activewatcher>/.venv/bin/activewatcher watch idle --server-url http://127.0.0.1:8712 --threshold-seconds 120
exec-once = $HOME/<path-to-activewatcher>/.venv/bin/activewatcher watch system --server-url http://127.0.0.1:8712 --poll-seconds 5.0
exec-once = $HOME/<path-to-activewatcher>/.venv/bin/activewatcher watch battery --server-url http://127.0.0.1:8712 --poll-seconds 15.0
```

## Stats Logs View

The `stats -> logs` page reads events from `bucket=window_visible`.
This stream is disabled by default unless visible-window tracking is enabled.

Enable it either by flag:

```bash
activewatcher watch hyprland --server-url http://127.0.0.1:8712 --track-visible-windows
```

or persistently in `~/.config/activewatcher/config.toml`:

```toml
[watch.hyprland]
track_visible_windows = true
visible_all_monitors = false
```

After changing this, restart the Hyprland watcher.

## Timers View

The UI includes top-level tabs: `dashboard`, `stats`, `timers`, `settings`.

- Create named entries as either `timer` (countdown) or `counter` (count up).
- Timer controls use `start work` / `start break` and `work done`.
- Counter controls use `start`, `pause`, and `stop`.
- Entries that were never started can be deleted directly from the active list.
- State is persisted in the local SQLite database.

## Settings View

- `white mode` toggle switches between dark and light themes.
- `high contrast` toggle increases readability/contrast.
- Timer end alerts can be enabled (`desktop notification` and `sound alert`).
- Optional API write token can be stored in UI settings for timer/autotag write actions.
- You can export tracked data and timers as JSON.
- Settings can be exported/imported and reset to defaults.
- Preferences are saved in browser local storage (for example `aw.ui.theme`).

## Terminal Dashboard (btop-style)

Run an interactive terminal dashboard directly in your shell:

```bash
activewatcher dashboard --server-url http://127.0.0.1:8712
```

Optional flags:

- `--refresh-seconds 1.0`
- `--range 24h|1w|1m|all`
- `--day-window midnight|rolling`

Controls in the dashboard:

- `q`: quit
- `r`: refresh now
- `1/2/3/4`: switch range (`24h`, `1w`, `1m`, `all`)
- `m`: toggle `day-window` mode (`midnight`/`rolling`)
- `h`: show/hide help

## Browser Plugins

Paths:

- Chromium/Brave: `extensions/browser-tabs/`
- Firefox signed package: `extensions/browser-tabs-firefox/activewatscher.xpi`

Install:

- Chromium/Brave: `chrome://extensions` -> Developer mode -> Load unpacked -> select `extensions/browser-tabs/`
- Firefox: `about:addons` -> gear icon -> Install Add-on From File -> select `extensions/browser-tabs-firefox/activewatscher.xpi`

If Firefox does not send data, open `about:debugging#/runtime/this-firefox`, click `Inspect` on the extension, and check for `[ActiveWatcher Tabs]` warnings in the console.

The plugin sends tab metrics to `bucket=browser_tabs`.

## Autotag Addon (LLM-assisted categories)

The repository includes a separate CLI for category suggestion and gated apply:

```bash
activewatcher-autotag scan --from 90d
activewatcher-autotag suggest --provider ollama --model qwen2.5:14b
activewatcher-autotag evaluate
activewatcher-autotag apply
```

Each run seeds both `review-gate.template.json` and `review-gate.json` in the run
directory. Before `apply`, update `review-gate.json` with human approval fields:

- `approved: true`
- `approved_by: <name>`
- `approved_at: <RFC3339 UTC>`

You can also approve directly in the web UI under `stats -> autotag`.

If you want to evaluate/apply without a prepared goldset, run:

```bash
activewatcher-autotag evaluate --allow-missing-goldset
```

Important defaults:

- DB is opened read-only.
- LLM is local-only (`ollama`).
- `apply` is blocked unless `review-gate.json` and `evaluation.json` pass all checks.
- `apply` requires explicit confirmation token `APPLY`.
- Updated categories are picked up automatically by the backend (no restart required).
