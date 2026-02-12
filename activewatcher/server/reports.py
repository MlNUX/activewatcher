from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from activewatcher.common.config import default_stale_after_seconds
from activewatcher.common.time import parse_rfc3339, to_rfc3339, to_utc, utcnow


@dataclass(frozen=True)
class Interval:
    id: int
    bucket: str
    source: str
    start: datetime
    end: datetime
    data: dict[str, Any]

    def duration_seconds(self) -> float:
        return max(0.0, (self.end - self.start).total_seconds())

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "bucket": self.bucket,
            "source": self.source,
            "start_ts": to_rfc3339(self.start),
            "end_ts": to_rfc3339(self.end),
            "data": self.data,
        }


def _parse_json(s: str) -> dict[str, Any]:
    try:
        value = json.loads(s)
    except json.JSONDecodeError:
        return {}
    if isinstance(value, dict):
        return value
    return {}


def _tzinfo(tz: str | None) -> timezone | ZoneInfo:
    if tz is None:
        return timezone.utc
    name = tz.strip()
    if not name or name.upper() == "UTC":
        return timezone.utc
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError as e:
        raise ValueError(f"unknown timezone: {name}") from e


def list_apps(
    conn: sqlite3.Connection,
    *,
    from_ts: datetime | None,
    to_ts: datetime | None,
    limit: int = 500,
) -> dict[str, Any]:
    now = utcnow()
    to_dt = to_utc(to_ts) if to_ts else now
    from_dt = to_utc(from_ts) if from_ts else (to_dt - timedelta(days=365))
    if to_dt < from_dt:
        from_dt, to_dt = to_dt, from_dt

    from_iso = to_rfc3339(from_dt)
    to_iso = to_rfc3339(to_dt)

    rows = conn.execute(
        """
        SELECT data_json
          FROM events
         WHERE bucket = 'window'
           AND start_ts < ?
           AND (end_ts IS NULL OR end_ts > ?)
         ORDER BY start_ts ASC
        """.strip(),
        (to_iso, from_iso),
    ).fetchall()

    apps: set[str] = set()
    for r in rows:
        data = _parse_json(str(r["data_json"]))
        app = str(data.get("app") or "")
        if not app or app.startswith("__"):
            continue
        apps.add(app)
        if len(apps) >= max(1, min(5000, int(limit))):
            break

    return {"from_ts": to_rfc3339(from_dt), "to_ts": to_rfc3339(to_dt), "apps": sorted(apps)}


def _add_seconds_by_local_day(
    out: dict[date, float],
    *,
    start: datetime,
    end: datetime,
    tz: timezone | ZoneInfo,
) -> None:
    if end <= start:
        return

    cur = start.astimezone(tz)
    end_local = end.astimezone(tz)

    while True:
        d = cur.date()
        next_midnight = datetime.combine(d + timedelta(days=1), time.min, tzinfo=tz)
        if next_midnight >= end_local:
            out[d] = out.get(d, 0.0) + max(0.0, (end_local - cur).total_seconds())
            return
        out[d] = out.get(d, 0.0) + max(0.0, (next_midnight - cur).total_seconds())
        cur = next_midnight


def heatmap(
    conn: sqlite3.Connection,
    *,
    from_ts: datetime | None,
    to_ts: datetime | None,
    tz: str | None,
    mode: str,
    apps: list[str] | None,
) -> dict[str, Any]:
    tzinfo = _tzinfo(tz)
    mode_norm = (mode or "").strip().lower() or "auto"
    if mode_norm not in ("auto", "active", "window"):
        raise ValueError('mode must be one of: "auto", "active", "window"')

    from_dt, to_dt, window = load_intervals(conn, bucket="window", source=None, from_ts=from_ts, to_ts=to_ts)
    _, _, idle = load_intervals(conn, bucket="idle", source=None, from_ts=from_dt, to_ts=to_dt)

    has_idle = bool(idle)
    if mode_norm == "window":
        mode_used = "window"
    elif mode_norm in ("auto", "active"):
        mode_used = "active" if has_idle else "window"
    else:
        mode_used = "window"

    app_filter: set[str] | None = None
    if apps:
        app_filter = {a.strip() for a in apps if a and a.strip()}
        if not app_filter:
            app_filter = None

    totals: dict[date, float] = {}

    if mode_used == "window":
        for it in window:
            app = str(it.data.get("app") or "")
            if not app or app.startswith("__"):
                continue
            if app_filter is not None and app not in app_filter:
                continue
            _add_seconds_by_local_day(totals, start=it.start, end=it.end, tz=tzinfo)
    else:
        active = [it for it in idle if it.data.get("afk") is False]

        a_idx = 0
        for w in window:
            app = str(w.data.get("app") or "")
            if not app or app.startswith("__"):
                continue
            if app_filter is not None and app not in app_filter:
                continue

            while a_idx < len(active) and active[a_idx].end <= w.start:
                a_idx += 1

            j = a_idx
            while j < len(active) and active[j].start < w.end:
                a = active[j]
                start = max(w.start, a.start)
                end = min(w.end, a.end)
                if end > start:
                    _add_seconds_by_local_day(totals, start=start, end=end, tz=tzinfo)
                if a.end <= w.end:
                    j += 1
                else:
                    break
            a_idx = j

    from_local = from_dt.astimezone(tzinfo).date()
    to_local = to_dt.astimezone(tzinfo).date()

    days: list[dict[str, Any]] = []
    max_seconds = 0.0
    d = from_local
    while d <= to_local:
        seconds = float(totals.get(d, 0.0))
        max_seconds = max(max_seconds, seconds)
        days.append({"date": d.isoformat(), "seconds": round(seconds, 3)})
        d += timedelta(days=1)

    return {
        "from_ts": to_rfc3339(from_dt),
        "to_ts": to_rfc3339(to_dt),
        "from_date": from_local.isoformat(),
        "to_date": to_local.isoformat(),
        "tz": str(tz or "UTC").strip() or "UTC",
        "mode": mode_used,
        "has_idle": has_idle,
        "apps": sorted(app_filter) if app_filter else [],
        "max_seconds": round(max_seconds, 3),
        "days": days,
    }


def load_intervals(
    conn: sqlite3.Connection,
    *,
    bucket: str | None,
    source: str | None,
    from_ts: datetime | None,
    to_ts: datetime | None,
) -> tuple[datetime, datetime, list[Interval]]:
    now = utcnow()
    to_dt = to_utc(to_ts) if to_ts else now
    from_dt = to_utc(from_ts) if from_ts else (to_dt - timedelta(hours=24))
    if to_dt < from_dt:
        from_dt, to_dt = to_dt, from_dt

    from_iso = to_rfc3339(from_dt)
    to_iso = to_rfc3339(to_dt)

    where = ["start_ts < ?", "(end_ts IS NULL OR end_ts > ?)"]
    params: list[Any] = [to_iso, from_iso]
    if bucket is not None:
        where.append("bucket = ?")
        params.append(bucket)
    if source is not None:
        where.append("source = ?")
        params.append(source)

    rows = conn.execute(
        f"""
        SELECT id, bucket, source, start_ts, end_ts, last_seen_ts, data_json
          FROM events
         WHERE {' AND '.join(where)}
         ORDER BY start_ts ASC
        """.strip(),
        tuple(params),
    ).fetchall()

    intervals: list[Interval] = []
    stale_after = default_stale_after_seconds()
    stale_before = to_dt - timedelta(seconds=stale_after) if stale_after > 0 else None
    for r in rows:
        start = parse_rfc3339(str(r["start_ts"]))
        end_raw = r["end_ts"]
        if end_raw is None:
            last_seen = parse_rfc3339(str(r["last_seen_ts"]))
            end = to_dt
            if stale_before is not None and last_seen < stale_before:
                end = min(last_seen, to_dt)
        else:
            end = parse_rfc3339(str(end_raw))

        start = max(start, from_dt)
        end = min(end, to_dt)
        if end <= start:
            continue

        intervals.append(
            Interval(
                id=int(r["id"]),
                bucket=str(r["bucket"]),
                source=str(r["source"]),
                start=start,
                end=end,
                data=_parse_json(str(r["data_json"])),
            )
        )

    return from_dt, to_dt, intervals


def data_range(
    conn: sqlite3.Connection,
    *,
    bucket: str | None = None,
    source: str | None = None,
) -> tuple[datetime | None, datetime | None]:
    where: list[str] = []
    params: list[Any] = []
    if bucket is not None:
        where.append("bucket = ?")
        params.append(bucket)
    if source is not None:
        where.append("source = ?")
        params.append(source)

    where_sql = f"WHERE {' AND '.join(where)}" if where else ""

    row = conn.execute(
        f"""
        SELECT MIN(start_ts) AS min_start_ts,
               MAX(COALESCE(end_ts, last_seen_ts)) AS max_end_ts
          FROM events
          {where_sql}
        """.strip(),
        tuple(params),
    ).fetchone()

    if row is None or row["min_start_ts"] is None or row["max_end_ts"] is None:
        return None, None

    try:
        from_dt = to_utc(parse_rfc3339(str(row["min_start_ts"])))
        to_dt = to_utc(parse_rfc3339(str(row["max_end_ts"])))
    except Exception:
        return None, None

    if to_dt < from_dt:
        from_dt, to_dt = to_dt, from_dt
    return from_dt, to_dt


@dataclass(frozen=True)
class TimelineSegment:
    start: datetime
    end: datetime
    window: dict[str, Any] | None
    afk: bool | None

    def duration_seconds(self) -> float:
        return max(0.0, (self.end - self.start).total_seconds())

    def to_json(self) -> dict[str, Any]:
        return {
            "start_ts": to_rfc3339(self.start),
            "end_ts": to_rfc3339(self.end),
            "afk": self.afk,
            "window": self.window,
        }


def _segment_key(seg: TimelineSegment) -> tuple:
    w = seg.window or {}
    return (
        seg.afk,
        w.get("app"),
        w.get("title"),
        w.get("workspace"),
        w.get("monitor"),
        w.get("xwayland"),
        w.get("no_focus"),
    )


def build_timeline(
    *,
    from_dt: datetime,
    to_dt: datetime,
    window_intervals: list[Interval],
    idle_intervals: list[Interval],
) -> list[TimelineSegment]:
    boundaries: set[datetime] = {from_dt, to_dt}
    for it in window_intervals:
        boundaries.add(it.start)
        boundaries.add(it.end)
    for it in idle_intervals:
        boundaries.add(it.start)
        boundaries.add(it.end)

    times = sorted(boundaries)
    window_intervals = sorted(window_intervals, key=lambda x: x.start)
    idle_intervals = sorted(idle_intervals, key=lambda x: x.start)

    w_idx = 0
    i_idx = 0
    segments: list[TimelineSegment] = []

    for a, b in zip(times, times[1:]):
        if b <= a:
            continue

        while w_idx < len(window_intervals) and window_intervals[w_idx].end <= a:
            w_idx += 1
        window = None
        if w_idx < len(window_intervals):
            w_it = window_intervals[w_idx]
            if w_it.start <= a < w_it.end:
                window = w_it.data

        while i_idx < len(idle_intervals) and idle_intervals[i_idx].end <= a:
            i_idx += 1
        afk: bool | None = None
        if i_idx < len(idle_intervals):
            i_it = idle_intervals[i_idx]
            if i_it.start <= a < i_it.end:
                afk = bool(i_it.data.get("afk", False))

        segments.append(TimelineSegment(start=a, end=b, window=window, afk=afk))

    if not segments:
        return []

    merged: list[TimelineSegment] = [segments[0]]
    for seg in segments[1:]:
        prev = merged[-1]
        if _segment_key(prev) == _segment_key(seg) and prev.end == seg.start:
            merged[-1] = TimelineSegment(start=prev.start, end=seg.end, window=prev.window, afk=prev.afk)
        else:
            merged.append(seg)
    return merged


def top_apps_total(segments: list[TimelineSegment]) -> list[dict[str, Any]]:
    totals: dict[str, float] = {}
    total_window = 0.0

    for seg in segments:
        if not seg.window:
            continue
        app = str(seg.window.get("app") or "")
        if not app or app.startswith("__"):
            continue
        dur = seg.duration_seconds()
        totals[app] = totals.get(app, 0.0) + dur
        total_window += dur

    items = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    out: list[dict[str, Any]] = []
    for app, seconds in items:
        out.append(
            {
                "app": app,
                "seconds": round(seconds, 3),
                "percent_window": round((seconds / total_window) * 100.0, 3) if total_window > 0 else 0.0,
            }
        )
    return out


def top_apps_active(segments: list[TimelineSegment]) -> list[dict[str, Any]]:
    totals: dict[str, float] = {}
    total_active = 0.0

    for seg in segments:
        if seg.afk is not False:
            continue
        if not seg.window:
            continue
        app = str(seg.window.get("app") or "")
        if not app or app.startswith("__"):
            continue
        dur = seg.duration_seconds()
        totals[app] = totals.get(app, 0.0) + dur
        total_active += dur

    items = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    out: list[dict[str, Any]] = []
    for app, seconds in items:
        out.append(
            {
                "app": app,
                "seconds": round(seconds, 3),
                "percent_active": round((seconds / total_active) * 100.0, 3) if total_active > 0 else 0.0,
            }
        )
    return out


def activity_totals(segments: list[TimelineSegment]) -> dict[str, Any]:
    total = 0.0
    afk = 0.0
    active = 0.0
    unknown = 0.0
    for seg in segments:
        dur = seg.duration_seconds()
        total += dur
        if seg.afk is True:
            afk += dur
        elif seg.afk is False:
            active += dur
        else:
            unknown += dur
    return {
        "total_seconds": round(total, 3),
        "afk_seconds": round(afk, 3),
        "active_seconds": round(active, 3),
        "unknown_seconds": round(unknown, 3),
    }


def chunk_timeline(
    *,
    from_dt: datetime,
    to_dt: datetime,
    segments: list[TimelineSegment],
    chunk_seconds: int,
) -> list[dict[str, Any]]:
    if chunk_seconds <= 0:
        return []

    out: list[dict[str, Any]] = []
    cursor = from_dt
    seg_idx = 0

    while cursor < to_dt:
        chunk_end = min(to_dt, cursor + timedelta(seconds=chunk_seconds))
        active = 0.0
        afk = 0.0
        unknown = 0.0
        app_totals: dict[str, float] = {}

        while seg_idx < len(segments) and segments[seg_idx].end <= cursor:
            seg_idx += 1

        j = seg_idx
        while j < len(segments):
            seg = segments[j]
            if seg.start >= chunk_end:
                break
            a = max(seg.start, cursor)
            b = min(seg.end, chunk_end)
            if b <= a:
                j += 1
                continue
            dur = (b - a).total_seconds()
            if seg.afk is True:
                afk += dur
            elif seg.afk is False:
                active += dur
                if seg.window:
                    app = str(seg.window.get("app") or "")
                    if app and not app.startswith("__"):
                        app_totals[app] = app_totals.get(app, 0.0) + dur
            else:
                unknown += dur
            j += 1

        top_app = None
        if app_totals:
            top_app = max(app_totals.items(), key=lambda kv: kv[1])[0]

        out.append(
            {
                "start_ts": to_rfc3339(cursor),
                "end_ts": to_rfc3339(chunk_end),
                "active_seconds": round(active, 3),
                "afk_seconds": round(afk, 3),
                "unknown_seconds": round(unknown, 3),
                "top_app": top_app,
            }
        )
        cursor = chunk_end

    return out


def summary(
    conn: sqlite3.Connection,
    *,
    from_ts: datetime | None,
    to_ts: datetime | None,
    chunk_seconds: int,
) -> dict[str, Any]:
    from_dt, to_dt, window = load_intervals(
        conn, bucket="window", source=None, from_ts=from_ts, to_ts=to_ts
    )
    _, _, idle = load_intervals(conn, bucket="idle", source=None, from_ts=from_dt, to_ts=to_dt)
    segments = build_timeline(from_dt=from_dt, to_dt=to_dt, window_intervals=window, idle_intervals=idle)

    apps_active = top_apps_active(segments)
    apps_total = top_apps_total(segments)
    has_idle = any(s.afk is not None for s in segments)

    return {
        "from_ts": to_rfc3339(from_dt),
        "to_ts": to_rfc3339(to_dt),
        **activity_totals(segments),
        "top_apps_mode": "active" if has_idle else "window",
        "top_apps": apps_active if has_idle else apps_total,
        "top_apps_active": apps_active,
        "top_apps_window": apps_total,
        "timeline": [s.to_json() for s in segments],
        "timeline_chunks": chunk_timeline(
            from_dt=from_dt, to_dt=to_dt, segments=segments, chunk_seconds=chunk_seconds
        ),
    }
