from __future__ import annotations

import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .runtime import ensure_autotag_dirs, parse_duration


def run_cleanup(*, older_than: str) -> dict[str, Any]:
    delta = parse_duration(older_than)
    now = datetime.now(timezone.utc)
    threshold_ts = now.timestamp() - delta.total_seconds()

    dirs = ensure_autotag_dirs()
    removed: list[str] = []
    kept: list[str] = []

    for path in sorted([p for p in dirs.runs.iterdir() if p.is_dir()]):
        mtime = path.stat().st_mtime
        if mtime <= threshold_ts:
            shutil.rmtree(path, ignore_errors=True)
            removed.append(path.name)
        else:
            kept.append(path.name)

    return {
        "older_than": older_than,
        "removed_runs": removed,
        "kept_runs": kept,
        "removed_count": len(removed),
        "kept_count": len(kept),
    }
