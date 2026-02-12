from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Optional

import typer

from activewatcher.common.config import default_db_path, default_server_url

app = typer.Typer(add_completion=False)
watch_app = typer.Typer(add_completion=False)
app.add_typer(watch_app, name="watch")


@app.command()
def server(
    host: str = typer.Option("127.0.0.1"),
    port: int = typer.Option(8712),
    db_path: Path = typer.Option(default_db_path()),
    log_level: str = typer.Option("info"),
) -> None:
    import uvicorn

    from activewatcher.server.app import create_app

    api = create_app(db_path)
    uvicorn.run(api, host=host, port=port, log_level=log_level)


@watch_app.command("hyprland")
def watch_hyprland(
    server_url: str = typer.Option(default_server_url()),
    source: str = typer.Option("hyprland"),
    debounce_ms: int = typer.Option(120),
    title_max_len: int = typer.Option(200),
    heartbeat_seconds: int = typer.Option(30),
    track_focused: bool = typer.Option(True, help="Track the focused window (bucket=window)."),
    track_visible_windows: bool = typer.Option(
        False, help="Track all visible windows (bucket=window_visible)."
    ),
    visible_all_monitors: bool = typer.Option(
        False, help="When tracking visible windows, include all monitors (default: focused monitor only)."
    ),
    track_open_apps: bool = typer.Option(False, help="Track all open apps (bucket=app_open)."),
    track_workspaces: bool = typer.Option(
        True,
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
    server_url: str = typer.Option(default_server_url()),
    source: str = typer.Option("logind"),
    threshold_seconds: int = typer.Option(120),
    poll_seconds: float = typer.Option(2.0),
    heartbeat_seconds: int = typer.Option(30),
    lock_process: str = typer.Option(
        "hyprlock",
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


@app.command()
def events(
    server_url: str = typer.Option(default_server_url()),
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
    server_url: str = typer.Option(default_server_url()),
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
