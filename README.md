# activewatcher

Local activity tracker for Linux/Wayland (Hyprland-focused).  
Runs locally on `http://127.0.0.1:8712`.

## Requirements

- Linux + Wayland (Hyprland for `watch hyprland`)
- Python `>= 3.11`

Minimal setup:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -U pip setuptools wheel
pip install -e . --no-build-isolation
```

## Security Defaults

- API CORS is restricted to local origins by default (`127.0.0.1`/`localhost` on ports `5173`, `5174`, `8712`).
- Host header checks are restricted to local hosts by default (`127.0.0.1`, `localhost`, `[::1]`).
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

## Browser Plugin

Extension path: `extensions/browser-tabs/`  
Supported: Brave, Chrome, Firefox

- Chromium/Brave: `chrome://extensions` -> Developer mode -> Load unpacked -> select `extensions/browser-tabs/`
- Firefox: `about:debugging#/runtime/this-firefox` -> Load Temporary Add-on

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
