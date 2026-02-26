from __future__ import annotations

import json
import os
import re
import socket
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from typing import Any, Iterable

from activewatcher.common.config import xdg_data_home
from activewatcher.common.time import parse_rfc3339, to_rfc3339, to_utc, utcnow

from .settings import RUNTIME_DEFAULTS

_DURATION_RE = re.compile(r"^(?P<value>\d+)(?P<unit>[smhdw])$", re.IGNORECASE)


@dataclass(frozen=True)
class RunDirs:
    root: Path
    runs: Path
    goldset: Path
    lockfile: Path


def autotag_dirs() -> RunDirs:
    root = xdg_data_home() / "activewatcher" / "autotag"
    return RunDirs(
        root=root,
        runs=root / "runs",
        goldset=root / "goldset",
        lockfile=root / ".run.lock",
    )


def ensure_autotag_dirs() -> RunDirs:
    dirs = autotag_dirs()
    dirs.root.mkdir(parents=True, exist_ok=True)
    dirs.runs.mkdir(parents=True, exist_ok=True)
    dirs.goldset.mkdir(parents=True, exist_ok=True)
    return dirs


def goldset_path() -> Path:
    return ensure_autotag_dirs().goldset / "goldset.v1.jsonl"


def plans_root() -> Path:
    return Path(__file__).resolve().parents[1] / "plans" / "autotag"


def prompts_dir() -> Path:
    return plans_root() / "prompts"


def schemas_dir() -> Path:
    return plans_root() / "schemas"


def now_utc() -> datetime:
    return utcnow()


def parse_duration(value: str) -> timedelta:
    raw = str(value or "").strip().lower()
    match = _DURATION_RE.fullmatch(raw)
    if not match:
        raise ValueError(f"invalid duration: {value}")
    n = int(match.group("value"))
    unit = match.group("unit")
    if unit == "s":
        return timedelta(seconds=n)
    if unit == "m":
        return timedelta(minutes=n)
    if unit == "h":
        return timedelta(hours=n)
    if unit == "d":
        return timedelta(days=n)
    return timedelta(weeks=n)


def resolve_time_spec(spec: str | None, *, now: datetime, default: str) -> datetime:
    raw = str(spec or default).strip()
    if not raw:
        raw = default
    if raw.lower() == "now":
        return now
    try:
        dt = parse_rfc3339(raw)
        return to_utc(dt)
    except Exception:
        pass
    delta = parse_duration(raw)
    return now - delta


def resolve_range(
    *,
    from_spec: str | None,
    to_spec: str | None,
    default_from: str = RUNTIME_DEFAULTS.default_from_window,
    default_to: str = RUNTIME_DEFAULTS.default_to_window,
) -> tuple[datetime, datetime]:
    now = now_utc()
    from_dt = resolve_time_spec(from_spec, now=now, default=default_from)
    to_dt = resolve_time_spec(to_spec, now=now, default=default_to)
    if to_dt < from_dt:
        from_dt, to_dt = to_dt, from_dt
    return from_dt, to_dt


def new_run_id(now: datetime | None = None) -> str:
    ts = to_rfc3339(now or now_utc()).replace(":", "").replace("-", "").replace(".", "")
    return f"run_{ts}_{uuid.uuid4().hex[:8]}"


def run_root(run_id: str) -> Path:
    return ensure_autotag_dirs().runs / str(run_id)


def create_run(run_id: str | None = None) -> Path:
    rid = run_id or new_run_id()
    path = run_root(rid)
    path.mkdir(parents=True, exist_ok=False)
    return path


def latest_run_root() -> Path:
    runs_dir = ensure_autotag_dirs().runs
    items = [p for p in runs_dir.iterdir() if p.is_dir()]
    if not items:
        raise FileNotFoundError("no autotag runs found")
    items.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return items[0]


def resolve_run_root(run_id: str | None) -> Path:
    if run_id:
        path = run_root(run_id)
        if not path.is_dir():
            raise FileNotFoundError(f"run not found: {run_id}")
        return path
    return latest_run_root()


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")))
            f.write("\n")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s:
                continue
            value = json.loads(s)
            if isinstance(value, dict):
                out.append(value)
    return out


def file_sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _process_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _lock_age_minutes(lock: dict[str, Any], *, now: datetime) -> float:
    started_raw = str(lock.get("started_at") or "").strip()
    if not started_raw:
        return 10_000.0
    try:
        started = to_utc(parse_rfc3339(started_raw))
    except Exception:
        return 10_000.0
    return max(0.0, (now - started).total_seconds() / 60.0)


@contextmanager
def run_lock(*, force_unlock: bool = False):
    dirs = ensure_autotag_dirs()
    lockfile = dirs.lockfile
    now = now_utc()

    if lockfile.exists():
        lock_data: dict[str, Any] = {}
        try:
            value = read_json(lockfile)
            if isinstance(value, dict):
                lock_data = value
        except Exception:
            lock_data = {}

        lock_pid = int(lock_data.get("pid") or 0)
        alive = _process_alive(lock_pid)
        age_minutes = _lock_age_minutes(lock_data, now=now)
        stale = (not alive) and age_minutes > float(
            RUNTIME_DEFAULTS.lock_stale_after_minutes
        )

        if force_unlock or stale:
            try:
                lockfile.unlink(missing_ok=True)
            except Exception:
                pass
        else:
            lock_run_id = str(lock_data.get("run_id") or "unknown")
            lock_host = str(lock_data.get("host") or "unknown")
            raise RuntimeError(
                f"autotag lock active (pid={lock_pid} host={lock_host} run_id={lock_run_id}); use --force-unlock to override"
            )

    current_lock = {
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "started_at": to_rfc3339(now),
        "run_id": "pending",
    }
    write_json(lockfile, current_lock)
    try:
        yield lockfile
    finally:
        try:
            raw = read_json(lockfile)
            if isinstance(raw, dict) and int(raw.get("pid") or 0) == os.getpid():
                lockfile.unlink(missing_ok=True)
        except Exception:
            pass


def set_lock_run_id(lockfile: Path, run_id: str) -> None:
    payload = {
        "pid": os.getpid(),
        "host": socket.gethostname(),
        "started_at": to_rfc3339(now_utc()),
        "run_id": run_id,
    }
    write_json(lockfile, payload)


def truncate_title(value: str, *, max_len: int = 80) -> str:
    s = str(value or "").strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 3].rstrip() + "..."


def redacted_url(raw_url: str) -> str:
    s = str(raw_url or "").strip()
    if not s:
        return ""
    if "?" in s:
        s = s.split("?", 1)[0]
    if "#" in s:
        s = s.split("#", 1)[0]
    return s


def utc_rfc3339(value: datetime) -> str:
    return to_rfc3339(value.astimezone(UTC))
