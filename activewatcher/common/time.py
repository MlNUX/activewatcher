from __future__ import annotations

from datetime import datetime, timezone


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def ensure_tzaware(dt: datetime) -> datetime:
    if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
        raise ValueError("timestamp must be timezone-aware")
    return dt


def to_utc(dt: datetime) -> datetime:
    return ensure_tzaware(dt).astimezone(timezone.utc)


def to_rfc3339(dt: datetime) -> str:
    dt_utc = to_utc(dt)
    s = dt_utc.isoformat(timespec="milliseconds")
    if s.endswith("+00:00"):
        s = s[:-6] + "Z"
    return s


def parse_rfc3339(value: str) -> datetime:
    v = value.strip()
    if v.endswith("Z"):
        v = v[:-1] + "+00:00"
    dt = datetime.fromisoformat(v)
    return ensure_tzaware(dt)
