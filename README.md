# activewatcher

Local activity tracker for Linux/Wayland (Hyprland-focused).  
Runs locally on `http://127.0.0.1:8712`.

## Requirements

- Linux + Wayland (Hyprland for `watch hyprland`)
- Python `>= 3.11`
- Optional: Node.js + npm (only for frontend dev/build)

Minimal setup:

```bash
python -m venv .venv
. .venv/bin/activate
pip install -U pip setuptools wheel
pip install -e . --no-build-isolation
```

## Autostart

In `~/.config/hypr/autostart.conf`:

```ini
exec-once = $HOME/<path-to-activewatcher>/.venv/bin/activewatcher server --host 127.0.0.1 --port 8712
exec-once = $HOME/<path-to-activewatcher>/.venv/bin/activewatcher watch hyprland --server-url http://127.0.0.1:8712
exec-once = $HOME/<path-to-activewatcher>/.venv/bin/activewatcher watch idle --server-url http://127.0.0.1:8712 --threshold-seconds 120
exec-once = $HOME/<path-to-activewatcher>/.venv/bin/activewatcher watch system --server-url http://127.0.0.1:8712 --poll-seconds 5.0
exec-once = $HOME/<path-to-activewatcher>/.venv/bin/activewatcher watch battery --server-url http://127.0.0.1:8712 --poll-seconds 15.0
```

## Browser Plugin

Extension path: `extensions/browser-tabs/`  
Supported: Brave, Chrome, Firefox

- Chromium/Brave: `chrome://extensions` -> Developer mode -> Load unpacked -> select `extensions/browser-tabs/`
- Firefox: `about:debugging#/runtime/this-firefox` -> Load Temporary Add-on

The plugin sends tab metrics to `bucket=browser_tabs`.  
Charts are visible in `/ui/stats` ("Browser Tabs").
