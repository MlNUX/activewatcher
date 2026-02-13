from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer

from activewatcher.common import config as app_config

app = typer.Typer(add_completion=False)
watch_app = typer.Typer(add_completion=False)
app.add_typer(watch_app, name="watch")


@app.command()
def server(
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8712),
    db_path: Path = typer.Option(app_config.default_db_path()),
    log_level: str = typer.Option("info"),
) -> None:
    import uvicorn

    from activewatcher.server.app import create_app

    api = create_app(db_path)
    uvicorn.run(api, host=host, port=port, log_level=log_level)


@watch_app.command("hyprland")
def watch_hyprland(
    server_url: str = typer.Option(app_config.default_server_url()),
    source: str = typer.Option(
        app_config.config_str(("watch", "hyprland", "source"), env_var="ACTIVEWATCHER_HYPRLAND_SOURCE", default="hyprland")
    ),
    debounce_ms: int = typer.Option(
        app_config.config_int(
            ("watch", "hyprland", "debounce_ms"), env_var="ACTIVEWATCHER_HYPRLAND_DEBOUNCE_MS", default=120
        )
    ),
    title_max_len: int = typer.Option(
        app_config.config_int(
            ("watch", "hyprland", "title_max_len"), env_var="ACTIVEWATCHER_HYPRLAND_TITLE_MAX_LEN", default=200
        )
    ),
    heartbeat_seconds: int = typer.Option(
        app_config.config_int(
            ("watch", "hyprland", "heartbeat_seconds"),
            env_var="ACTIVEWATCHER_HYPRLAND_HEARTBEAT_SECONDS",
            default=30,
        )
    ),
    track_focused: bool = typer.Option(
        app_config.config_bool(("watch", "hyprland", "track_focused"), env_var="ACTIVEWATCHER_TRACK_FOCUSED", default=True),
        help="Track the focused window (bucket=window).",
    ),
    track_visible_windows: bool = typer.Option(
        app_config.config_bool(
            ("watch", "hyprland", "track_visible_windows"),
            env_var="ACTIVEWATCHER_TRACK_VISIBLE_WINDOWS",
            default=False,
        ),
        help="Track all visible windows (bucket=window_visible).",
    ),
    visible_all_monitors: bool = typer.Option(
        app_config.config_bool(
            ("watch", "hyprland", "visible_all_monitors"),
            env_var="ACTIVEWATCHER_VISIBLE_ALL_MONITORS",
            default=False,
        ),
        help="When tracking visible windows, include all monitors (default: focused monitor only).",
    ),
    track_open_apps: bool = typer.Option(
        app_config.config_bool(("watch", "hyprland", "track_open_apps"), env_var="ACTIVEWATCHER_TRACK_OPEN_APPS", default=False),
        help="Track all open apps (bucket=app_open).",
    ),
    track_workspaces: bool = typer.Option(
        app_config.config_bool(("watch", "hyprland", "track_workspaces"), env_var="ACTIVEWATCHER_TRACK_WORKSPACES", default=True),
        help="Track workspace switches (bucket=workspace) and switch events (bucket=workspace_switch).",
    ),
) -> None:
    from activewatcher.watchers import hyprland as hypr_watcher

    asyncio.run(
        hypr_watcher.run(
            server_url=server_url,
            source=source,
            debounce_ms=debounce_ms,
            title_max_len=title_max_len,
            heartbeat_seconds=heartbeat_seconds,
            track_focused=track_focused,
            track_visible_windows=track_visible_windows,
            visible_all_monitors=visible_all_monitors,
            track_open_apps=track_open_apps,
            track_workspaces=track_workspaces,
        )
    )


@watch_app.command("idle")
def watch_idle(
    server_url: str = typer.Option(app_config.default_server_url()),
    source: str = typer.Option(
        app_config.config_str(("watch", "idle", "source"), env_var="ACTIVEWATCHER_IDLE_SOURCE", default="logind")
    ),
    threshold_seconds: int = typer.Option(
        app_config.config_int(
            ("watch", "idle", "threshold_seconds"), env_var="ACTIVEWATCHER_IDLE_THRESHOLD_SECONDS", default=120
        )
    ),
    poll_seconds: float = typer.Option(
        app_config.config_float(("watch", "idle", "poll_seconds"), env_var="ACTIVEWATCHER_IDLE_POLL_SECONDS", default=5.0)
    ),
    heartbeat_seconds: int = typer.Option(
        app_config.config_int(
            ("watch", "idle", "heartbeat_seconds"), env_var="ACTIVEWATCHER_IDLE_HEARTBEAT_SECONDS", default=30
        )
    ),
    lock_process: str = typer.Option(
        app_config.config_str(
            ("watch", "idle", "lock_process"),
            env_var="ACTIVEWATCHER_IDLE_LOCK_PROCESS",
            default="hyprlock",
            allow_empty=True,
        ),
        help='Treat as AFK while this process is running (set to "" to disable).',
    ),
) -> None:
    from activewatcher.watchers import idle as idle_watcher

    asyncio.run(
        idle_watcher.run(
            server_url=server_url,
            source=source,
            threshold_seconds=threshold_seconds,
            poll_seconds=poll_seconds,
            heartbeat_seconds=heartbeat_seconds,
            lock_process=lock_process,
        )
    )


@watch_app.command("system")
def watch_system(
    server_url: str = typer.Option(app_config.default_server_url()),
    source: str = typer.Option(
        app_config.config_str(("watch", "system", "source"), env_var="ACTIVEWATCHER_SYSTEM_SOURCE", default="system")
    ),
    poll_seconds: float = typer.Option(
        app_config.config_float(
            ("watch", "system", "poll_seconds"), env_var="ACTIVEWATCHER_SYSTEM_POLL_SECONDS", default=5.0
        )
    ),
    heartbeat_seconds: int = typer.Option(
        app_config.config_int(
            ("watch", "system", "heartbeat_seconds"), env_var="ACTIVEWATCHER_SYSTEM_HEARTBEAT_SECONDS", default=30
        )
    ),
    include_loopback: bool = typer.Option(
        app_config.config_bool(
            ("watch", "system", "include_loopback"), env_var="ACTIVEWATCHER_SYSTEM_INCLUDE_LOOPBACK", default=False
        ),
        help="Include loopback traffic (lo) in network metrics.",
    ),
) -> None:
    from activewatcher.watchers import system as system_watcher

    asyncio.run(
        system_watcher.run(
            server_url=server_url,
            source=source,
            poll_seconds=poll_seconds,
            heartbeat_seconds=heartbeat_seconds,
            include_loopback=include_loopback,
        )
    )


@app.command()
def events(
    server_url: str = typer.Option(app_config.default_server_url()),
    bucket: Optional[str] = typer.Option(None),
    source: Optional[str] = typer.Option(None),
    from_ts: Optional[str] = typer.Option(None, "--from"),
    to_ts: Optional[str] = typer.Option(None, "--to"),
) -> None:
    from activewatcher.common.http import ActiveWatcherClient

    client = ActiveWatcherClient(server_url)
    try:
        params = {}
        if bucket:
            params["bucket"] = bucket
        if source:
            params["source"] = source
        if from_ts:
            params["from"] = from_ts
        if to_ts:
            params["to"] = to_ts
        data = client.get_json("/v1/events", params=params)
    finally:
        client.close()
    print(json.dumps(data, indent=2, ensure_ascii=False))


@app.command()
def summary(
    server_url: str = typer.Option(app_config.default_server_url()),
    from_ts: Optional[str] = typer.Option(None, "--from"),
    to_ts: Optional[str] = typer.Option(None, "--to"),
    chunk_seconds: int = typer.Option(300),
) -> None:
    from activewatcher.common.http import ActiveWatcherClient

    client = ActiveWatcherClient(server_url)
    try:
        params = {"chunk_seconds": chunk_seconds}
        if from_ts:
            params["from"] = from_ts
        if to_ts:
            params["to"] = to_ts
        data = client.get_json("/v1/summary", params=params)
    finally:
        client.close()
    print(json.dumps(data, indent=2, ensure_ascii=False))
