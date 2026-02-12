from __future__ import annotations

import os
from pathlib import Path

APP_NAME = "activewatcher"


def xdg_data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))


def default_data_dir() -> Path:
    return xdg_data_home() / APP_NAME


def default_db_path() -> Path:
    raw = os.environ.get("ACTIVEWATCHER_DB_PATH")
    if raw:
        return Path(raw)
    return default_data_dir() / "events.sqlite3"


def default_server_url() -> str:
    return os.environ.get("ACTIVEWATCHER_SERVER_URL", "http://127.0.0.1:8712")


def default_stale_after_seconds() -> int:
    raw = os.environ.get("ACTIVEWATCHER_STALE_AFTER_SECONDS", "120")
    try:
        value = int(raw)
    except ValueError:
        return 120
    return max(0, value)


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
