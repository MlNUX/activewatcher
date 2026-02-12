from __future__ import annotations

from functools import lru_cache
from pathlib import Path

_UI_PATH = Path(__file__).with_name("ui.html")


@lru_cache(maxsize=1)
def _read_ui_html_cached(mtime_ns: int) -> str:
    # Cache content by file mtime so edits to ui.html are picked up automatically.
    return _UI_PATH.read_text(encoding="utf-8")


def get_ui_html() -> str:
    try:
        mtime_ns = _UI_PATH.stat().st_mtime_ns
    except FileNotFoundError as e:
        raise RuntimeError(f"UI template not found: {_UI_PATH}") from e
    return _read_ui_html_cached(mtime_ns)


# Backward compatibility for older imports.
UI_HTML = get_ui_html()
