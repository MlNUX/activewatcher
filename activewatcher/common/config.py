from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python >=3.11 in this project
    tomllib = None

APP_NAME = "activewatcher"


def xdg_data_home() -> Path:
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))


def default_data_dir() -> Path:
    return xdg_data_home() / APP_NAME


def xdg_config_home() -> Path:
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


def default_config_path() -> Path:
    raw = os.environ.get("ACTIVEWATCHER_CONFIG_PATH")
    if raw:
        return Path(raw)
    return xdg_config_home() / APP_NAME / "config.toml"


@lru_cache(maxsize=1)
def _load_runtime_config() -> dict[str, Any]:
    path = default_config_path()
    if not path.is_file() or tomllib is None:
        return {}
    try:
        with path.open("rb") as f:
            loaded = tomllib.load(f)
    except Exception:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _path_parts(path: str | tuple[str, ...]) -> tuple[str, ...]:
    if isinstance(path, tuple):
        return path
    return tuple(p for p in path.split(".") if p)


def _config_value(path: str | tuple[str, ...]) -> Any:
    parts = _path_parts(path)
    node: Any = _load_runtime_config()
    for part in parts:
        if not isinstance(node, dict):
            return None
        node = node.get(part)
    return node


def _parse_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        s = value.strip().lower()
        if s in ("1", "true", "yes", "on"):
            return True
        if s in ("0", "false", "no", "off"):
            return False
    return None


def _parse_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            return int(s)
        except ValueError:
            return None
    return None


def _parse_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        try:
            return float(s)
        except ValueError:
            return None
    return None


def _parse_str(value: Any, *, allow_empty: bool = False) -> str | None:
    if value is None:
        return None
    s = str(value).strip()
    if s or allow_empty:
        return s
    return None


def config_bool(path: str | tuple[str, ...], *, env_var: str | None = None, default: bool) -> bool:
    if env_var:
        from_env = _parse_bool(os.environ.get(env_var))
        if from_env is not None:
            return from_env
    from_cfg = _parse_bool(_config_value(path))
    if from_cfg is not None:
        return from_cfg
    return default


def config_int(path: str | tuple[str, ...], *, env_var: str | None = None, default: int) -> int:
    if env_var:
        from_env = _parse_int(os.environ.get(env_var))
        if from_env is not None:
            return from_env
    from_cfg = _parse_int(_config_value(path))
    if from_cfg is not None:
        return from_cfg
    return default


def config_float(path: str | tuple[str, ...], *, env_var: str | None = None, default: float) -> float:
    if env_var:
        from_env = _parse_float(os.environ.get(env_var))
        if from_env is not None:
            return from_env
    from_cfg = _parse_float(_config_value(path))
    if from_cfg is not None:
        return from_cfg
    return default


def config_str(
    path: str | tuple[str, ...], *, env_var: str | None = None, default: str, allow_empty: bool = False
) -> str:
    if env_var:
        from_env = _parse_str(os.environ.get(env_var), allow_empty=allow_empty)
        if from_env is not None:
            return from_env
    from_cfg = _parse_str(_config_value(path), allow_empty=allow_empty)
    if from_cfg is not None:
        return from_cfg
    return default


def default_db_path() -> Path:
    raw = os.environ.get("ACTIVEWATCHER_DB_PATH")
    if raw:
        return Path(raw)
    return default_data_dir() / "events.sqlite3"


def default_categories_path() -> Path:
    raw = os.environ.get("ACTIVEWATCHER_CATEGORIES_PATH")
    if raw:
        return Path(raw)
    return default_data_dir() / "categories.json"


def default_server_url() -> str:
    return config_str(
        ("watch", "server_url"),
        env_var="ACTIVEWATCHER_SERVER_URL",
        default="http://127.0.0.1:8712",
    )


def default_stale_after_seconds() -> int:
    value = config_int(
        ("server", "stale_after_seconds"),
        env_var="ACTIVEWATCHER_STALE_AFTER_SECONDS",
        default=120,
    )
    return max(0, value)


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
