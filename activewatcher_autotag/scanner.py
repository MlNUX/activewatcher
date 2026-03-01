from __future__ import annotations

import sqlite3
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from activewatcher.common.time import to_rfc3339
from activewatcher.server import reports

from .runtime import redacted_url, truncate_title, write_json, write_jsonl
from .settings import RUNTIME_DEFAULTS, THRESHOLDS

_MULTI_PART_SUFFIXES = {
    "co.uk",
    "org.uk",
    "ac.uk",
    "gov.uk",
    "com.au",
    "net.au",
    "org.au",
    "co.nz",
    "co.in",
    "co.jp",
    "co.kr",
    "co.id",
    "co.il",
    "com.br",
    "com.mx",
    "com.ar",
    "com.tr",
    "com.pl",
    "com.ru",
    "com.cn",
    "com.tw",
    "com.hk",
    "com.sg",
    "com.my",
    "com.ph",
    "com.sa",
    "com.ng",
}

_APP_ALIASES = {
    "google chrome": "chrome",
    "chromium browser": "chromium",
    "visual studio code": "code",
    "code - oss": "code",
    "firefox developer edition": "firefox",
    "brave browser": "brave",
}


@dataclass(frozen=True)
class ScanStats:
    window_intervals: int
    tab_intervals: int
    app_entities: int
    domain_entities: int


def _tzinfo(tz_name: str) -> timezone | ZoneInfo:
    raw = str(tz_name or "UTC").strip()
    if not raw or raw.upper() == "UTC":
        return timezone.utc
    try:
        return ZoneInfo(raw)
    except ZoneInfoNotFoundError as e:
        raise ValueError(f"unknown timezone: {raw}") from e


def _normalize_app(value: str) -> str:
    app = str(value or "").strip().lower()
    if not app:
        return ""
    return _APP_ALIASES.get(app, app)


def _base_domain(host: str) -> str:
    h = str(host or "").strip().lower()
    if not h or "." not in h:
        return h
    parts = [p for p in h.split(".") if p]
    if len(parts) <= 2:
        return h
    tld2 = ".".join(parts[-2:])
    if tld2 in _MULTI_PART_SUFFIXES and len(parts) >= 3:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def normalize_domain(raw_url: str) -> str:
    s = str(raw_url or "").strip()
    if not s:
        return ""
    clean = redacted_url(s)
    parsed = urlparse(clean if "://" in clean else f"http://{clean}")
    host = str(parsed.hostname or "").strip().lower()
    if host.startswith("www."):
        host = host[4:]
    if not host:
        return ""
    base = _base_domain(host)
    return base or host


def _add_seconds_by_local_day(
    out: dict[date, float],
    *,
    start: datetime,
    end: datetime,
    tz: timezone | ZoneInfo,
    weight: float = 1.0,
) -> None:
    if end <= start or weight <= 0:
        return
    cur = start.astimezone(tz)
    end_local = end.astimezone(tz)
    while True:
        d = cur.date()
        next_midnight = datetime.combine(d + timedelta(days=1), time.min, tzinfo=tz)
        if next_midnight >= end_local:
            out[d] = out.get(d, 0.0) + (
                max(0.0, (end_local - cur).total_seconds()) * weight
            )
            return
        out[d] = out.get(d, 0.0) + (
            max(0.0, (next_midnight - cur).total_seconds()) * weight
        )
        cur = next_midnight


def _top_names(weighted: dict[str, float], *, limit: int = 8) -> list[str]:
    rows = sorted(weighted.items(), key=lambda kv: kv[1], reverse=True)
    return [name for name, _ in rows[: max(1, int(limit))] if name]


def _active_days(day_totals: dict[date, float]) -> int:
    return sum(
        1 for _, sec in day_totals.items() if sec >= THRESHOLDS.active_day_min_seconds
    )


def connect_readonly(db_path: Path) -> sqlite3.Connection:
    path = Path(db_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"database not found: {path}")
    uri = f"file:{path}?mode=ro"
    conn = sqlite3.connect(uri, uri=True, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def build_profiles(
    conn: sqlite3.Connection,
    *,
    from_dt: datetime,
    to_dt: datetime,
    tz_name: str,
) -> tuple[list[dict[str, Any]], ScanStats]:
    tz = _tzinfo(tz_name)
    _, _, window_intervals = reports.load_intervals(
        conn,
        bucket="window",
        source=None,
        from_ts=from_dt,
        to_ts=to_dt,
    )
    _, _, tab_intervals = reports.load_intervals(
        conn,
        bucket="browser_tabs",
        source=None,
        from_ts=from_dt,
        to_ts=to_dt,
    )

    app_seconds: dict[str, float] = defaultdict(float)
    app_occurrences: dict[str, int] = defaultdict(int)
    app_titles: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    app_domains: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    app_days: dict[str, dict[date, float]] = defaultdict(dict)

    domain_seconds: dict[str, float] = defaultdict(float)
    domain_occurrences: dict[str, int] = defaultdict(int)
    domain_titles: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    domain_apps: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    domain_days: dict[str, dict[date, float]] = defaultdict(dict)
    co_domains: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))

    for it in window_intervals:
        app_raw = str(it.data.get("app") or "")
        app = _normalize_app(app_raw)
        if not app or app.startswith("__"):
            continue
        sec = it.duration_seconds()
        if sec <= 0:
            continue
        app_seconds[app] += sec
        app_occurrences[app] += 1
        title = truncate_title(str(it.data.get("title") or ""), max_len=80)
        if title:
            app_titles[app][title] += sec
        day_map = app_days[app]
        _add_seconds_by_local_day(day_map, start=it.start, end=it.end, tz=tz)

    for it in tab_intervals:
        tabs = it.data.get("tabs")
        if not isinstance(tabs, list) or not tabs:
            continue
        sec = it.duration_seconds()
        if sec <= 0:
            continue
        browser = _normalize_app(str(it.data.get("browser") or it.source or "browser"))
        domains_in_event: set[str] = set()
        tab_rows = [tab for tab in tabs if isinstance(tab, dict)]
        if not tab_rows:
            continue
        weighted_sec = sec / float(len(tab_rows))
        weight_per_tab = 1.0 / float(len(tab_rows))

        for tab in tab_rows:
            raw_url = str(
                tab.get("url") or tab.get("pending_url") or tab.get("pendingUrl") or ""
            )
            domain = normalize_domain(raw_url)
            if not domain:
                continue
            title = truncate_title(str(tab.get("title") or ""), max_len=80)
            domain_seconds[domain] += weighted_sec
            domain_occurrences[domain] += 1
            domain_apps[domain][browser] += weighted_sec
            if title:
                domain_titles[domain][title] += weighted_sec
            day_map = domain_days[domain]
            _add_seconds_by_local_day(
                day_map,
                start=it.start,
                end=it.end,
                tz=tz,
                weight=weight_per_tab,
            )

            domains_in_event.add(domain)
            if browser:
                app_domains[browser][domain] += weighted_sec

        if len(domains_in_event) > 1:
            limited = sorted(domains_in_event)[:40]
            for i, left in enumerate(limited):
                for right in limited[i + 1 :]:
                    co_domains[left][right] += sec
                    co_domains[right][left] += sec

    profiles: list[dict[str, Any]] = []

    for app, sec in sorted(app_seconds.items(), key=lambda kv: kv[1], reverse=True):
        profiles.append(
            {
                "entity_id": f"app:{app}",
                "entity_type": "app",
                "entity": app,
                "seconds": round(sec, 3),
                "occurrences": int(app_occurrences.get(app, 0)),
                "active_days": _active_days(app_days.get(app, {})),
                "top_titles": _top_names(app_titles.get(app, {}), limit=8),
                "top_domains": _top_names(app_domains.get(app, {}), limit=8),
                "co_occurring_apps": [],
                "co_occurring_domains": _top_names(app_domains.get(app, {}), limit=8),
                "from_ts": to_rfc3339(from_dt),
                "to_ts": to_rfc3339(to_dt),
            }
        )

    for domain, sec in sorted(
        domain_seconds.items(), key=lambda kv: kv[1], reverse=True
    ):
        profiles.append(
            {
                "entity_id": f"domain:{domain}",
                "entity_type": "domain",
                "entity": domain,
                "seconds": round(sec, 3),
                "occurrences": int(domain_occurrences.get(domain, 0)),
                "active_days": _active_days(domain_days.get(domain, {})),
                "top_titles": _top_names(domain_titles.get(domain, {}), limit=8),
                "top_domains": [domain],
                "co_occurring_apps": _top_names(domain_apps.get(domain, {}), limit=8),
                "co_occurring_domains": _top_names(co_domains.get(domain, {}), limit=8),
                "from_ts": to_rfc3339(from_dt),
                "to_ts": to_rfc3339(to_dt),
            }
        )

    seen: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for p in profiles:
        entity_id = str(p.get("entity_id") or "")
        if not entity_id or entity_id in seen:
            continue
        seen.add(entity_id)
        deduped.append(p)

    stats = ScanStats(
        window_intervals=len(window_intervals),
        tab_intervals=len(tab_intervals),
        app_entities=len(app_seconds),
        domain_entities=len(domain_seconds),
    )
    return deduped, stats


def run_scan(
    *,
    run_root: Path,
    db_path: Path,
    from_dt: datetime,
    to_dt: datetime,
    tz_name: str,
    categories_path: Path,
) -> dict[str, Any]:
    conn = connect_readonly(db_path)
    try:
        profiles, stats = build_profiles(
            conn, from_dt=from_dt, to_dt=to_dt, tz_name=tz_name
        )
    finally:
        conn.close()

    write_jsonl(run_root / "entity-profiles.jsonl", profiles)
    metadata = {
        "run_id": run_root.name,
        "created_at": to_rfc3339(datetime.now(timezone.utc)),
        "db_path": str(db_path),
        "categories_path": str(categories_path),
        "from_ts": to_rfc3339(from_dt),
        "to_ts": to_rfc3339(to_dt),
        "timezone": tz_name,
        "enable_title_regex": RUNTIME_DEFAULTS.enable_title_regex,
        "scan": {
            "window_intervals": stats.window_intervals,
            "tab_intervals": stats.tab_intervals,
            "app_entities": stats.app_entities,
            "domain_entities": stats.domain_entities,
            "total_entities": len(profiles),
        },
    }
    write_json(run_root / "run-metadata.json", metadata)
    return metadata
