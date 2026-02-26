from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from activewatcher.common.categories import CategoryCatalog, category_catalog
from activewatcher.common.config import default_stale_after_seconds, xdg_data_home
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


def _merge_ranges(
    ranges: list[tuple[datetime, datetime]],
) -> list[tuple[datetime, datetime]]:
    if not ranges:
        return []
    items = [(s, e) for s, e in ranges if e > s]
    if not items:
        return []
    items.sort(key=lambda r: r[0])
    merged: list[tuple[datetime, datetime]] = []
    cur_start, cur_end = items[0]
    for start, end in items[1:]:
        if start <= cur_end:
            if end > cur_end:
                cur_end = end
            continue
        merged.append((cur_start, cur_end))
        cur_start, cur_end = start, end
    merged.append((cur_start, cur_end))
    return merged


def _sum_ranges(ranges: list[tuple[datetime, datetime]]) -> float:
    return sum(max(0.0, (end - start).total_seconds()) for start, end in ranges)


def _sum_overlap(
    ranges: list[tuple[datetime, datetime]], start: datetime, end: datetime
) -> float:
    if end <= start:
        return 0.0
    total = 0.0
    for r_start, r_end in ranges:
        if r_end <= start:
            continue
        if r_start >= end:
            break
        a = max(r_start, start)
        b = min(r_end, end)
        if b > a:
            total += (b - a).total_seconds()
    return total


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

    return {
        "from_ts": to_rfc3339(from_dt),
        "to_ts": to_rfc3339(to_dt),
        "apps": sorted(apps),
    }


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

    from_dt, to_dt, window = load_intervals(
        conn, bucket="window", source=None, from_ts=from_ts, to_ts=to_ts
    )
    _, _, idle = load_intervals(
        conn, bucket="idle", source=None, from_ts=from_dt, to_ts=to_dt
    )

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
         WHERE {" AND ".join(where)}
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
            merged[-1] = TimelineSegment(
                start=prev.start, end=seg.end, window=prev.window, afk=prev.afk
            )
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
                "percent_window": round((seconds / total_window) * 100.0, 3)
                if total_window > 0
                else 0.0,
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
                "percent_active": round((seconds / total_active) * 100.0, 3)
                if total_active > 0
                else 0.0,
            }
        )
    return out


def chunk_timeline(
    *,
    from_dt: datetime,
    to_dt: datetime,
    segments: list[TimelineSegment],
    runtime_ranges: list[tuple[datetime, datetime]],
    afk_ranges: list[tuple[datetime, datetime]],
    chunk_seconds: int,
) -> list[dict[str, Any]]:
    if chunk_seconds <= 0:
        return []

    out: list[dict[str, Any]] = []
    cursor = from_dt
    seg_idx = 0
    runtime_ranges = sorted(runtime_ranges, key=lambda r: r[0])
    afk_ranges = sorted(afk_ranges, key=lambda r: r[0])

    while cursor < to_dt:
        chunk_end = min(to_dt, cursor + timedelta(seconds=chunk_seconds))
        bucket_sec = max(0.0, (chunk_end - cursor).total_seconds())
        runtime = _sum_overlap(runtime_ranges, cursor, chunk_end)
        afk = _sum_overlap(afk_ranges, cursor, chunk_end)
        if afk > runtime:
            afk = runtime
        active = max(0.0, runtime - afk)
        unknown = max(0.0, bucket_sec - runtime)
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
            if seg.afk is False and seg.window:
                app = str(seg.window.get("app") or "")
                if app and not app.startswith("__"):
                    app_totals[app] = app_totals.get(app, 0.0) + dur
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
    _, _, idle = load_intervals(
        conn, bucket="idle", source=None, from_ts=from_dt, to_ts=to_dt
    )
    _, _, all_events = load_intervals(
        conn, bucket=None, source=None, from_ts=from_dt, to_ts=to_dt
    )
    segments = build_timeline(
        from_dt=from_dt, to_dt=to_dt, window_intervals=window, idle_intervals=idle
    )

    apps_active = top_apps_active(segments)
    apps_total = top_apps_total(segments)
    has_idle = any(s.afk is not None for s in segments)

    total_seconds = max(0.0, (to_dt - from_dt).total_seconds())
    runtime_ranges = _merge_ranges([(it.start, it.end) for it in all_events])
    runtime_seconds = min(total_seconds, _sum_ranges(runtime_ranges))
    afk_ranges = _merge_ranges(
        [(it.start, it.end) for it in idle if bool(it.data.get("afk", False))]
    )
    afk_seconds = min(runtime_seconds, _sum_ranges(afk_ranges))
    active_seconds = max(0.0, runtime_seconds - afk_seconds)
    unknown_seconds = max(0.0, total_seconds - runtime_seconds)

    return {
        "from_ts": to_rfc3339(from_dt),
        "to_ts": to_rfc3339(to_dt),
        "total_seconds": round(total_seconds, 3),
        "active_seconds": round(active_seconds, 3),
        "afk_seconds": round(afk_seconds, 3),
        "unknown_seconds": round(unknown_seconds, 3),
        "top_apps_mode": "active" if has_idle else "window",
        "top_apps": apps_active if has_idle else apps_total,
        "top_apps_active": apps_active,
        "top_apps_window": apps_total,
        "timeline": [s.to_json() for s in segments],
        "timeline_chunks": chunk_timeline(
            from_dt=from_dt,
            to_dt=to_dt,
            segments=segments,
            runtime_ranges=runtime_ranges,
            afk_ranges=afk_ranges,
            chunk_seconds=chunk_seconds,
        ),
    }


def _add_cat_seconds(totals: dict[str, float], cat: str, seconds: float) -> None:
    if seconds <= 0:
        return
    key = str(cat or "other")
    totals[key] = totals.get(key, 0.0) + seconds


def _add_cat_named_seconds(
    totals: dict[str, dict[str, float]],
    *,
    category: str,
    name: str,
    seconds: float,
) -> None:
    if seconds <= 0:
        return
    cat = str(category or "other")
    key = str(name or "").strip()
    if not key:
        return
    per_cat = totals.setdefault(cat, {})
    per_cat[key] = per_cat.get(key, 0.0) + seconds


def _top_named_rows(
    totals: dict[str, float], *, limit: int = 8
) -> list[dict[str, Any]]:
    return [
        {"name": name, "seconds": round(sec, 3)}
        for name, sec in sorted(totals.items(), key=lambda kv: kv[1], reverse=True)[
            : max(1, int(limit))
        ]
        if sec > 0
    ]


def _tab_domain_from_url(raw_url: str) -> str:
    s = str(raw_url or "").strip()
    if not s:
        return "internal"
    parsed = urlparse(s if "://" in s else f"http://{s}")
    host = str(parsed.hostname or "").strip().lower()
    if host.startswith("www."):
        host = host[4:]
    if host:
        return host
    scheme = str(parsed.scheme or "").strip().lower()
    if scheme and scheme not in ("http", "https"):
        return scheme
    return "internal"


def _app_category_details_from_segments(
    catalog: CategoryCatalog, segments: list[TimelineSegment], *, only_active: bool
) -> dict[str, dict[str, Any]]:
    apps_by_cat: dict[str, dict[str, float]] = {}
    titles_by_cat: dict[str, dict[str, float]] = {}

    for seg in segments:
        if not seg.window:
            continue
        if only_active and seg.afk is not False:
            continue
        dur = seg.duration_seconds()
        if dur <= 0:
            continue
        app = str(seg.window.get("app") or "")
        if not app or app.startswith("__"):
            continue
        title = str(seg.window.get("title") or "")
        cat = catalog.classify_app(app=app, title=title)
        _add_cat_named_seconds(apps_by_cat, category=cat, name=app, seconds=dur)
        if title:
            _add_cat_named_seconds(titles_by_cat, category=cat, name=title, seconds=dur)

    out: dict[str, dict[str, Any]] = {}
    all_cats = set(apps_by_cat) | set(titles_by_cat)
    for cat in all_cats:
        out[cat] = {
            "top_apps": _top_named_rows(apps_by_cat.get(cat, {}), limit=8),
            "top_titles": _top_named_rows(titles_by_cat.get(cat, {}), limit=8),
        }
    return out


def _app_category_details_from_intervals(
    catalog: CategoryCatalog, intervals: list[Interval]
) -> dict[str, dict[str, Any]]:
    apps_by_cat: dict[str, dict[str, float]] = {}
    titles_by_cat: dict[str, dict[str, float]] = {}

    for it in intervals:
        dur = it.duration_seconds()
        if dur <= 0:
            continue
        app = str(it.data.get("app") or "")
        if not app or app.startswith("__"):
            continue
        title = str(it.data.get("title") or "")
        cat = catalog.classify_app(app=app, title=title)
        _add_cat_named_seconds(apps_by_cat, category=cat, name=app, seconds=dur)
        if title:
            _add_cat_named_seconds(titles_by_cat, category=cat, name=title, seconds=dur)

    out: dict[str, dict[str, Any]] = {}
    all_cats = set(apps_by_cat) | set(titles_by_cat)
    for cat in all_cats:
        out[cat] = {
            "top_apps": _top_named_rows(apps_by_cat.get(cat, {}), limit=8),
            "top_titles": _top_named_rows(titles_by_cat.get(cat, {}), limit=8),
        }
    return out


def _tabs_category_details(
    catalog: CategoryCatalog, intervals: list[Interval]
) -> dict[str, dict[str, Any]]:
    domains_by_cat: dict[str, dict[str, float]] = {}
    titles_by_cat: dict[str, dict[str, float]] = {}
    browsers_by_cat: dict[str, dict[str, float]] = {}

    for it in intervals:
        tabs = it.data.get("tabs")
        if not isinstance(tabs, list) or not tabs:
            continue
        dur = it.duration_seconds()
        if dur <= 0:
            continue
        browser = str(it.data.get("browser") or it.source or "browser")

        for tab in tabs:
            if not isinstance(tab, dict):
                continue
            url = str(
                tab.get("url") or tab.get("pending_url") or tab.get("pendingUrl") or ""
            )
            title = str(tab.get("title") or "")
            cat = catalog.classify_tab(url=url, title=title, app=browser)
            domain = _tab_domain_from_url(url)

            _add_cat_named_seconds(
                domains_by_cat, category=cat, name=domain, seconds=dur
            )
            _add_cat_named_seconds(
                browsers_by_cat, category=cat, name=browser, seconds=dur
            )
            if title:
                _add_cat_named_seconds(
                    titles_by_cat, category=cat, name=title, seconds=dur
                )

    out: dict[str, dict[str, Any]] = {}
    all_cats = set(domains_by_cat) | set(titles_by_cat) | set(browsers_by_cat)
    for cat in all_cats:
        out[cat] = {
            "top_domains": _top_named_rows(domains_by_cat.get(cat, {}), limit=8),
            "top_titles": _top_named_rows(titles_by_cat.get(cat, {}), limit=8),
            "top_browsers": _top_named_rows(browsers_by_cat.get(cat, {}), limit=6),
        }
    return out


def _category_rows(
    catalog: CategoryCatalog, totals: dict[str, float]
) -> tuple[list[dict[str, Any]], float]:
    total_seconds = sum(max(0.0, float(v)) for v in totals.values())
    rows: list[dict[str, Any]] = []
    for r in catalog.rules:
        sec = max(0.0, float(totals.get(r.id, 0.0)))
        if sec <= 0 and total_seconds > 0:
            continue
        rows.append(
            {
                "category": r.id,
                "label": r.label,
                "color": r.color,
                "seconds": round(sec, 3),
                "percent": round((sec / total_seconds) * 100.0, 3)
                if total_seconds > 0
                else 0.0,
            }
        )
    if not rows:
        meta = catalog.category_meta()
        fallback = (
            meta[-1]
            if meta
            else {"id": "other", "label": "Other", "color": "rgba(255,255,255,.45)"}
        )
        rows = [
            {
                "category": fallback["id"],
                "label": fallback["label"],
                "color": fallback["color"],
                "seconds": 0.0,
                "percent": 0.0,
            }
        ]
    return rows, round(total_seconds, 3)


def _app_category_totals_from_segments(
    catalog: CategoryCatalog, segments: list[TimelineSegment], *, only_active: bool
) -> dict[str, float]:
    totals: dict[str, float] = {}
    for seg in segments:
        if not seg.window:
            continue
        if only_active and seg.afk is not False:
            continue
        app = str(seg.window.get("app") or "")
        if not app or app.startswith("__"):
            continue
        title = str(seg.window.get("title") or "")
        cat = catalog.classify_app(app=app, title=title)
        _add_cat_seconds(totals, cat, seg.duration_seconds())
    return totals


def _app_category_totals_from_intervals(
    catalog: CategoryCatalog, intervals: list[Interval]
) -> dict[str, float]:
    totals: dict[str, float] = {}
    for it in intervals:
        app = str(it.data.get("app") or "")
        if not app or app.startswith("__"):
            continue
        title = str(it.data.get("title") or "")
        cat = catalog.classify_app(app=app, title=title)
        _add_cat_seconds(totals, cat, it.duration_seconds())
    return totals


def _tabs_category_totals(
    catalog: CategoryCatalog, intervals: list[Interval]
) -> dict[str, float]:
    totals: dict[str, float] = {}
    for it in intervals:
        tabs = it.data.get("tabs")
        if not isinstance(tabs, list) or not tabs:
            continue
        browser = str(it.data.get("browser") or it.source or "")
        dur = it.duration_seconds()
        if dur <= 0:
            continue
        for t in tabs:
            if not isinstance(t, dict):
                continue
            url = str(t.get("url") or t.get("pending_url") or t.get("pendingUrl") or "")
            title = str(t.get("title") or "")
            cat = catalog.classify_tab(url=url, title=title, app=browser)
            _add_cat_seconds(totals, cat, dur)
    return totals


def categories_summary(
    conn: sqlite3.Connection,
    *,
    from_ts: datetime | None,
    to_ts: datetime | None,
    mode: str = "auto",
) -> dict[str, Any]:
    mode_norm = (mode or "").strip().lower() or "auto"
    if mode_norm not in ("auto", "active", "window", "visible"):
        raise ValueError('mode must be one of: "auto", "active", "window", "visible"')

    catalog = category_catalog()
    app_totals: dict[str, float] = {}
    app_details: dict[str, dict[str, Any]] = {}
    app_mode = "window"

    if mode_norm == "visible":
        from_dt, to_dt, visible = load_intervals(
            conn, bucket="window_visible", source=None, from_ts=from_ts, to_ts=to_ts
        )
        app_mode = "visible"
        app_totals = _app_category_totals_from_intervals(catalog, visible)
        app_details = _app_category_details_from_intervals(catalog, visible)
    else:
        from_dt, to_dt, window = load_intervals(
            conn, bucket="window", source=None, from_ts=from_ts, to_ts=to_ts
        )
        _, _, idle = load_intervals(
            conn, bucket="idle", source=None, from_ts=from_dt, to_ts=to_dt
        )
        segments = build_timeline(
            from_dt=from_dt, to_dt=to_dt, window_intervals=window, idle_intervals=idle
        )
        use_active = mode_norm == "active" or (mode_norm == "auto" and bool(idle))
        app_mode = "active" if use_active else "window"
        app_totals = _app_category_totals_from_segments(
            catalog, segments, only_active=use_active
        )
        app_details = _app_category_details_from_segments(
            catalog, segments, only_active=use_active
        )

    _, _, tabs = load_intervals(
        conn, bucket="browser_tabs", source=None, from_ts=from_dt, to_ts=to_dt
    )
    tabs_totals = _tabs_category_totals(catalog, tabs)
    tab_details = _tabs_category_details(catalog, tabs)

    app_rows, app_total_seconds = _category_rows(catalog, app_totals)
    tab_rows, tab_total_seconds = _category_rows(catalog, tabs_totals)

    return {
        "from_ts": to_rfc3339(from_dt),
        "to_ts": to_rfc3339(to_dt),
        "mode": app_mode,
        "catalog_source": catalog.source,
        "categories": catalog.category_meta(),
        "apps_total_seconds": app_total_seconds,
        "tabs_total_seconds": tab_total_seconds,
        "apps": app_rows,
        "tabs": tab_rows,
        "app_details": app_details,
        "tab_details": tab_details,
    }


def _autotag_runs_dir() -> Path:
    return xdg_data_home() / "activewatcher" / "autotag" / "runs"


def _autotag_run_roots(*, limit: int = 50) -> list[Path]:
    runs_dir = _autotag_runs_dir()
    if not runs_dir.is_dir():
        return []
    out = [p for p in runs_dir.iterdir() if p.is_dir()]
    out.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return out[: max(1, min(500, int(limit)))]


def _read_json_file(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return value if isinstance(value, dict) else {}


def _read_jsonl_file(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    out: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            s = line.strip()
            if not s:
                continue
            value = json.loads(s)
            if isinstance(value, dict):
                out.append(value)
    except Exception:
        return []
    return out


def _file_sha256(path: Path) -> str:
    h = sha256()
    with path.open("rb") as f:
        while True:
            chunk = f.read(65536)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def _select_autotag_run_root(*, run_id: str | None, limit: int = 500) -> Path | None:
    roots = _autotag_run_roots(limit=limit)
    if run_id:
        wanted = str(run_id)
        for root in roots:
            if root.name == wanted:
                return root
        raise FileNotFoundError(f"autotag run not found: {run_id}")
    if roots:
        return roots[0]
    return None


def _normalize_review_gate_drop_ids(values: Any) -> list[str]:
    if not isinstance(values, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        cat_id = str(value or "").strip().lower()
        if not cat_id or cat_id in seen:
            continue
        seen.add(cat_id)
        out.append(cat_id)
    return out


def _review_gate_payload_from_source(
    *,
    root: Path,
    payload: dict[str, Any],
    source: str,
) -> dict[str, Any]:
    return {
        "source": source,
        "run_id": str(payload.get("run_id") or root.name),
        "approved": bool(payload.get("approved") or False),
        "approved_by": str(payload.get("approved_by") or ""),
        "approved_at": str(payload.get("approved_at") or ""),
        "categories_generated_sha256": str(
            payload.get("categories_generated_sha256") or ""
        ),
        "allowed_category_drop_ids": _normalize_review_gate_drop_ids(
            payload.get("allowed_category_drop_ids")
        ),
    }


def _read_autotag_review_gate(root: Path) -> dict[str, Any]:
    review_gate = _read_json_file(root / "review-gate.json")
    if review_gate:
        return _review_gate_payload_from_source(
            root=root,
            payload=review_gate,
            source="review-gate.json",
        )

    review_template = _read_json_file(root / "review-gate.template.json")
    if review_template:
        return _review_gate_payload_from_source(
            root=root,
            payload=review_template,
            source="review-gate.template.json",
        )

    return {
        "source": "missing",
        "run_id": root.name,
        "approved": False,
        "approved_by": "",
        "approved_at": "",
        "categories_generated_sha256": "",
        "allowed_category_drop_ids": [],
    }


def list_autotag_runs(*, limit: int = 50) -> dict[str, Any]:
    roots = _autotag_run_roots(limit=limit)
    rows: list[dict[str, Any]] = []
    for root in roots:
        metadata = _read_json_file(root / "run-metadata.json")
        suggest_raw = metadata.get("suggest")
        suggest: dict[str, Any] = suggest_raw if isinstance(suggest_raw, dict) else {}
        pass_a_raw = suggest.get("pass_a")
        pass_a: dict[str, Any] = pass_a_raw if isinstance(pass_a_raw, dict) else {}
        pass_b_raw = suggest.get("pass_b")
        pass_b: dict[str, Any] = pass_b_raw if isinstance(pass_b_raw, dict) else {}
        evaluate_raw = metadata.get("evaluate")
        evaluate: dict[str, Any] = (
            evaluate_raw if isinstance(evaluate_raw, dict) else {}
        )
        review_gate = _read_autotag_review_gate(root)
        decision_count = len(_read_jsonl_file(root / "autotag-decisions.jsonl"))
        rows.append(
            {
                "run_id": root.name,
                "created_at": str(metadata.get("created_at") or ""),
                "from_ts": str(metadata.get("from_ts") or ""),
                "to_ts": str(metadata.get("to_ts") or ""),
                "decision_count": decision_count,
                "categories_generated_sha256": str(
                    suggest.get("categories_generated_sha256") or ""
                ),
                "pass_a_failed_batches": int(pass_a.get("failed_batches") or 0),
                "pass_b_failed_batches": int(pass_b.get("failed_batches") or 0),
                "pass_b_apply_blocked": bool(pass_b.get("apply_blocked") or False),
                "pass_b_apply_block_reason": str(
                    pass_b.get("apply_block_reason") or ""
                ),
                "recommend_apply": bool(evaluate.get("recommend_apply") or False),
                "review_gate_approved": bool(review_gate.get("approved") or False),
            }
        )

    latest_run_id = str(rows[0].get("run_id") or "") if rows else ""
    return {
        "runs": rows,
        "latest_run_id": latest_run_id,
    }


def autotag_generated(*, run_id: str | None) -> dict[str, Any]:
    selected = _select_autotag_run_root(run_id=run_id, limit=500)

    if selected is None:
        return {
            "run_id": "",
            "from_ts": "",
            "to_ts": "",
            "categories_generated_sha256": "",
            "generated": {},
            "review_gate": {
                "source": "missing",
                "run_id": "",
                "approved": False,
                "approved_by": "",
                "approved_at": "",
                "categories_generated_sha256": "",
                "allowed_category_drop_ids": [],
            },
        }

    metadata = _read_json_file(selected / "run-metadata.json")
    suggest_raw = metadata.get("suggest")
    suggest: dict[str, Any] = suggest_raw if isinstance(suggest_raw, dict) else {}
    categories_sha = str(suggest.get("categories_generated_sha256") or "")
    generated = _read_json_file(selected / "categories.generated.json")
    review_gate = _read_autotag_review_gate(selected)

    return {
        "run_id": selected.name,
        "from_ts": str(metadata.get("from_ts") or ""),
        "to_ts": str(metadata.get("to_ts") or ""),
        "categories_generated_sha256": categories_sha,
        "generated": generated,
        "review_gate": review_gate,
    }


def approve_autotag_review_gate(
    *,
    run_id: str,
    approved_by: str,
    allowed_category_drop_ids: list[str] | None,
) -> dict[str, Any]:
    rid = str(run_id or "").strip()
    if not rid:
        raise ValueError("run_id is required")
    approved_by_clean = str(approved_by or "").strip()
    if not approved_by_clean:
        raise ValueError("approved_by is required")

    selected = _select_autotag_run_root(run_id=rid, limit=500)
    if selected is None:
        raise FileNotFoundError(f"autotag run not found: {run_id}")

    generated_sha = ""
    generated_path = selected / "categories.generated.json"
    if generated_path.is_file():
        generated_sha = _file_sha256(generated_path)

    review_existing = _read_json_file(selected / "review-gate.json")
    review_template = _read_json_file(selected / "review-gate.template.json")
    review_source: dict[str, Any] = review_existing or review_template

    if not generated_sha:
        generated_sha = str(review_source.get("categories_generated_sha256") or "")
    if not generated_sha:
        metadata = _read_json_file(selected / "run-metadata.json")
        suggest_raw = metadata.get("suggest")
        suggest = suggest_raw if isinstance(suggest_raw, dict) else {}
        generated_sha = str(suggest.get("categories_generated_sha256") or "")
    if not generated_sha:
        raise ValueError("missing categories generated sha for run")

    payload = {
        "run_id": selected.name,
        "approved": True,
        "approved_by": approved_by_clean,
        "approved_at": to_rfc3339(utcnow()),
        "categories_generated_sha256": generated_sha,
        "allowed_category_drop_ids": _normalize_review_gate_drop_ids(
            allowed_category_drop_ids
        ),
    }
    (selected / "review-gate.json").write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return {
        "run_id": selected.name,
        "review_gate": _review_gate_payload_from_source(
            root=selected,
            payload=payload,
            source="review-gate.json",
        ),
    }


def autotag_decisions(
    *,
    run_id: str | None,
    limit: int = 500,
    decision_type: str | None = None,
    state: str | None = None,
) -> dict[str, Any]:
    selected = _select_autotag_run_root(run_id=run_id, limit=500)

    if selected is None:
        return {
            "run_id": "",
            "from_ts": "",
            "to_ts": "",
            "decision_count": 0,
            "total_decision_count": 0,
            "summary": {
                "by_type": {},
                "by_state": {},
                "by_target": {},
                "avg_confidence": 0.0,
            },
            "decisions": [],
        }

    metadata = _read_json_file(selected / "run-metadata.json")
    rows = _read_jsonl_file(selected / "autotag-decisions.jsonl")
    total_decision_count = len(rows)

    type_filter = str(decision_type or "").strip().lower()
    state_filter = str(state or "").strip().lower()
    filtered: list[dict[str, Any]] = []
    by_type: dict[str, int] = {}
    by_state: dict[str, int] = {}
    by_target: dict[str, int] = {}
    conf_total = 0.0
    conf_count = 0

    for row in rows:
        row_type = str(row.get("decision_type") or "").strip().lower()
        row_state = str(row.get("state") or "").strip().lower()
        if type_filter and row_type != type_filter:
            continue
        if state_filter and row_state != state_filter:
            continue

        target = str(row.get("target_category_id") or "").strip().lower() or "unknown"
        by_type[row_type or "unknown"] = by_type.get(row_type or "unknown", 0) + 1
        by_state[row_state or "unknown"] = by_state.get(row_state or "unknown", 0) + 1
        by_target[target] = by_target.get(target, 0) + 1

        try:
            conf = float(row.get("confidence") or 0.0)
            conf_total += conf
            conf_count += 1
        except Exception:
            pass

        reasons_raw = row.get("reasons")
        reasons: list[Any] = reasons_raw if isinstance(reasons_raw, list) else []
        risk_flags_raw = row.get("risk_flags")
        risk_flags: list[Any] = (
            risk_flags_raw if isinstance(risk_flags_raw, list) else []
        )

        filtered.append(
            {
                "created_at": str(row.get("created_at") or ""),
                "decision_type": row_type,
                "entity_id": str(row.get("entity_id") or ""),
                "entity_type": str(row.get("entity_type") or ""),
                "entity": str(row.get("entity") or ""),
                "state": row_state,
                "target_category_id": target,
                "confidence": float(row.get("confidence") or 0.0),
                "reasons": [str(v) for v in reasons[:3]],
                "risk_flags": [str(v) for v in risk_flags[:5]],
            }
        )

    filtered.sort(
        key=lambda r: (
            str(r.get("created_at") or ""),
            str(r.get("entity_id") or ""),
        ),
        reverse=True,
    )
    bounded = filtered[: max(1, min(5000, int(limit)))]

    return {
        "run_id": selected.name,
        "from_ts": str(metadata.get("from_ts") or ""),
        "to_ts": str(metadata.get("to_ts") or ""),
        "decision_count": len(filtered),
        "total_decision_count": total_decision_count,
        "summary": {
            "by_type": by_type,
            "by_state": by_state,
            "by_target": by_target,
            "avg_confidence": round((conf_total / conf_count), 4)
            if conf_count
            else 0.0,
        },
        "decisions": bounded,
    }
