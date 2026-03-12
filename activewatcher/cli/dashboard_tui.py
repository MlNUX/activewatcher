from __future__ import annotations

import curses
import json
import math
import time
from dataclasses import dataclass
from datetime import datetime, time as dt_time, timedelta, timezone
from typing import Any
from urllib.parse import urlparse

from activewatcher.common.http import ActiveWatcherClient
from activewatcher.common.models import END_MARKER_KEY
from activewatcher.common.time import parse_rfc3339, to_rfc3339, to_utc, utcnow


RANGE_KEYS = ("24h", "1w", "1m", "all")
DAY_WINDOW_MODES = ("midnight", "rolling")
EVENTS_CHUNK_SECONDS = 7 * 24 * 3600
EVENTS_MAX_CHUNKS = 48


@dataclass(frozen=True)
class TimeWindow:
    from_ts: str
    to_ts: str


@dataclass(frozen=True)
class ActivityBlock:
    active_seconds: float
    afk_seconds: float
    off_seconds: float
    total_seconds: float
    top_apps: list[tuple[str, float]]


@dataclass(frozen=True)
class SystemBlock:
    cpu_percent: float
    mem_percent: float
    net_total_mb_s: float
    cpu_history: list[float]
    mem_history: list[float]
    net_history: list[float]
    top_interfaces: list[tuple[str, float]]


@dataclass(frozen=True)
class TimersBlock:
    total: int
    running: int
    paused: int
    rows: list[str]


@dataclass(frozen=True)
class WorkspacesBlock:
    switch_count: int
    top_pairs: list[tuple[str, str, int]]


@dataclass(frozen=True)
class TabsBlock:
    latest_count: int
    top_domains: list[tuple[str, float]]


@dataclass(frozen=True)
class BatteryBlock:
    available: bool
    capacity_percent: float | None
    status: str
    mains_online: bool | None


@dataclass(frozen=True)
class DashboardSnapshot:
    fetched_at: datetime
    window: TimeWindow
    range_key: str
    day_window_mode: str
    activity: ActivityBlock
    system: SystemBlock
    timers: TimersBlock
    workspaces: WorkspacesBlock
    tabs: TabsBlock
    battery: BatteryBlock | None
    errors: list[str]


def normalize_dashboard_range(raw: str) -> str:
    value = str(raw or "").strip().lower()
    if value in RANGE_KEYS:
        return value
    raise ValueError(f"range must be one of: {', '.join(RANGE_KEYS)}")


def normalize_day_window_mode(raw: str) -> str:
    value = str(raw or "").strip().lower()
    if value in DAY_WINDOW_MODES:
        return value
    raise ValueError(f"day-window must be one of: {', '.join(DAY_WINDOW_MODES)}")


def render_bar(value: float, total: float, width: int) -> str:
    if width <= 0:
        return ""
    if total <= 0:
        return "-" * width
    ratio = max(0.0, min(1.0, value / total))
    filled = int(round(ratio * width))
    filled = max(0, min(width, filled))
    return "#" * filled + "-" * (width - filled)


def render_sparkline(values: list[float], width: int) -> str:
    if width <= 0:
        return ""
    if not values:
        return "." * width

    levels = " .:-=+*#%@"
    sampled: list[float] = []
    if width == 1:
        sampled = [values[-1]]
    else:
        last = max(1, len(values) - 1)
        for i in range(width):
            idx = int(round((i / float(width - 1)) * last))
            idx = max(0, min(last, idx))
            sampled.append(float(values[idx]))

    lo = min(sampled)
    hi = max(sampled)
    if math.isclose(lo, hi, rel_tol=0.0, abs_tol=1e-12):
        ch = levels[len(levels) // 2]
        return ch * width

    out: list[str] = []
    scale = float(len(levels) - 1)
    span = hi - lo
    for v in sampled:
        ratio = (v - lo) / span
        idx = int(round(ratio * scale))
        idx = max(0, min(len(levels) - 1, idx))
        out.append(levels[idx])
    return "".join(out)


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        out = float(value)
    except Exception:
        return default
    if math.isnan(out) or math.isinf(out):
        return default
    return out


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except Exception:
        return default


def _fmt_seconds_short(seconds: float) -> str:
    total = max(0, int(round(_safe_float(seconds, 0.0))))
    h = total // 3600
    m = (total % 3600) // 60
    s = total % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"


def _trim(text: str, width: int) -> str:
    if width <= 0:
        return ""
    value = str(text or "")
    if len(value) <= width:
        return value
    if width <= 3:
        return value[:width]
    return value[: width - 3] + "..."


def _parse_ts(value: Any) -> datetime | None:
    raw = str(value or "").strip()
    if not raw:
        return None
    try:
        return to_utc(parse_rfc3339(raw))
    except Exception:
        return None


def _event_overlap_seconds(
    event: dict[str, Any], *, from_dt: datetime, to_dt: datetime
) -> float:
    start = _parse_ts(event.get("start_ts"))
    end = _parse_ts(event.get("end_ts"))
    if start is None or end is None or end <= start:
        return 0.0
    a = max(start, from_dt)
    b = min(end, to_dt)
    if b <= a:
        return 0.0
    return max(0.0, (b - a).total_seconds())


def _event_point_ts(event: dict[str, Any]) -> datetime | None:
    end = _parse_ts(event.get("end_ts"))
    if end is not None:
        return end
    return _parse_ts(event.get("start_ts"))


def _domain_from_url(raw: str) -> str:
    s = str(raw or "").strip()
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


def _resolve_window(
    client: ActiveWatcherClient, *, range_key: str, day_window_mode: str
) -> TimeWindow:
    now = utcnow()
    if range_key == "24h":
        if day_window_mode == "midnight":
            local_now = now.astimezone()
            local_midnight = datetime.combine(
                local_now.date(), dt_time.min, tzinfo=local_now.tzinfo
            )
            from_dt = to_utc(local_midnight)
            return TimeWindow(from_ts=to_rfc3339(from_dt), to_ts=to_rfc3339(now))
        return TimeWindow(
            from_ts=to_rfc3339(now - timedelta(hours=24)), to_ts=to_rfc3339(now)
        )

    if range_key == "1w":
        local_now = now.astimezone()
        week_start_date = local_now.date() - timedelta(days=local_now.weekday())
        week_start = datetime.combine(
            week_start_date, dt_time.min, tzinfo=local_now.tzinfo
        )
        return TimeWindow(from_ts=to_rfc3339(to_utc(week_start)), to_ts=to_rfc3339(now))

    if range_key == "1m":
        local_now = now.astimezone()
        month_start = datetime(
            local_now.year, local_now.month, 1, tzinfo=local_now.tzinfo
        )
        return TimeWindow(
            from_ts=to_rfc3339(to_utc(month_start)), to_ts=to_rfc3339(now)
        )

    fallback = TimeWindow(
        from_ts=to_rfc3339(now - timedelta(hours=24)), to_ts=to_rfc3339(now)
    )
    try:
        payload = client.get_json("/v1/range")
    except Exception:
        return fallback

    if bool(payload.get("empty", False)):
        return fallback
    from_ts = str(payload.get("from_ts") or "").strip()
    if not from_ts:
        return fallback
    return TimeWindow(from_ts=from_ts, to_ts=to_rfc3339(now))


def _pick_chunk_seconds(range_key: str, *, from_ts: str, to_ts: str) -> int:
    if range_key == "24h":
        return 3600
    if range_key in ("1w", "1m"):
        return 86400

    from_dt = _parse_ts(from_ts)
    to_dt = _parse_ts(to_ts)
    if from_dt is None or to_dt is None or to_dt <= from_dt:
        return 3600

    duration = max(1.0, (to_dt - from_dt).total_seconds())
    target = duration / 60.0
    steps = [
        300,
        900,
        1800,
        3600,
        7200,
        14400,
        21600,
        43200,
        86400,
        172800,
        604800,
        1209600,
        2592000,
    ]
    for step in steps:
        if target <= step:
            return step
    return 2592000


def _events_payload_to_rows(payload: Any) -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    rows = payload.get("events")
    if not isinstance(rows, list):
        return []
    out: list[dict[str, Any]] = []
    for row in rows:
        if isinstance(row, dict):
            out.append(row)
    return out


def _event_dedupe_key(event: dict[str, Any]) -> str:
    event_id = event.get("id")
    if isinstance(event_id, int):
        return f"id:{event_id}"
    source = str(event.get("source") or "")
    start_ts = str(event.get("start_ts") or "")
    end_ts = str(event.get("end_ts") or "")
    data = event.get("data")
    if isinstance(data, dict):
        try:
            data_json = json.dumps(
                data, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            )
        except Exception:
            data_json = "{}"
    else:
        data_json = "{}"
    return f"{source}|{start_ts}|{end_ts}|{data_json}"


def _split_window_for_events(window: TimeWindow) -> list[TimeWindow]:
    from_dt = _parse_ts(window.from_ts)
    to_dt = _parse_ts(window.to_ts)
    if from_dt is None or to_dt is None or to_dt <= from_dt:
        return [window]

    duration_seconds = max(1.0, (to_dt - from_dt).total_seconds())
    chunk_seconds = max(60, int(EVENTS_CHUNK_SECONDS))
    min_chunk_seconds = int(math.ceil(duration_seconds / float(EVENTS_MAX_CHUNKS)))
    if min_chunk_seconds > chunk_seconds:
        chunk_seconds = min_chunk_seconds

    out: list[TimeWindow] = []
    cursor = from_dt
    while cursor < to_dt:
        chunk_end = min(to_dt, cursor + timedelta(seconds=chunk_seconds))
        out.append(TimeWindow(from_ts=to_rfc3339(cursor), to_ts=to_rfc3339(chunk_end)))
        cursor = chunk_end

    return out or [window]


def _build_activity_block(summary_payload: Any) -> ActivityBlock:
    if not isinstance(summary_payload, dict):
        return ActivityBlock(
            active_seconds=0.0,
            afk_seconds=0.0,
            off_seconds=0.0,
            total_seconds=0.0,
            top_apps=[],
        )

    top_apps_rows: list[tuple[str, float]] = []
    top_apps = summary_payload.get("top_apps")
    if isinstance(top_apps, list):
        for row in top_apps:
            if not isinstance(row, dict):
                continue
            app = str(row.get("app") or "").strip()
            if not app:
                continue
            seconds = max(0.0, _safe_float(row.get("seconds"), 0.0))
            top_apps_rows.append((app, seconds))

    top_apps_rows.sort(key=lambda item: item[1], reverse=True)
    top_apps_rows = top_apps_rows[:8]

    return ActivityBlock(
        active_seconds=max(
            0.0, _safe_float(summary_payload.get("active_seconds"), 0.0)
        ),
        afk_seconds=max(0.0, _safe_float(summary_payload.get("afk_seconds"), 0.0)),
        off_seconds=max(0.0, _safe_float(summary_payload.get("unknown_seconds"), 0.0)),
        total_seconds=max(0.0, _safe_float(summary_payload.get("total_seconds"), 0.0)),
        top_apps=top_apps_rows,
    )


def _build_system_block(
    events: list[dict[str, Any]], *, from_dt: datetime, to_dt: datetime
) -> SystemBlock:
    cpu_history: list[tuple[datetime, float]] = []
    mem_history: list[tuple[datetime, float]] = []
    net_history: list[tuple[datetime, float]] = []
    iface_seconds: dict[str, float] = {}

    latest_ts: datetime | None = None
    latest_cpu = 0.0
    latest_mem = 0.0
    latest_net = 0.0

    for event in events:
        data = event.get("data")
        if not isinstance(data, dict):
            continue

        ts = _event_point_ts(event)
        if ts is None:
            continue

        cpu = max(0.0, min(100.0, _safe_float(data.get("cpu_percent"), 0.0)))
        mem = max(0.0, min(100.0, _safe_float(data.get("mem_percent"), 0.0)))

        net_total_bps = max(0.0, _safe_float(data.get("net_total_bps"), 0.0))
        if net_total_bps <= 0.0:
            net_total_bps = max(0.0, _safe_float(data.get("net_rx_bps"), 0.0)) + max(
                0.0, _safe_float(data.get("net_tx_bps"), 0.0)
            )
        net_mb_s = net_total_bps / 1_000_000.0

        cpu_history.append((ts, cpu))
        mem_history.append((ts, mem))
        net_history.append((ts, net_mb_s))

        overlap = _event_overlap_seconds(event, from_dt=from_dt, to_dt=to_dt)
        if overlap > 0.0:
            net_ifaces = data.get("net_interfaces")
            if isinstance(net_ifaces, list):
                for raw in net_ifaces:
                    iface = str(raw or "").strip()
                    if not iface:
                        continue
                    iface_seconds[iface] = iface_seconds.get(iface, 0.0) + overlap

        if latest_ts is None or ts >= latest_ts:
            latest_ts = ts
            latest_cpu = cpu
            latest_mem = mem
            latest_net = net_mb_s

    cpu_history.sort(key=lambda item: item[0])
    mem_history.sort(key=lambda item: item[0])
    net_history.sort(key=lambda item: item[0])

    top_interfaces = sorted(
        iface_seconds.items(), key=lambda item: item[1], reverse=True
    )[:4]

    return SystemBlock(
        cpu_percent=latest_cpu,
        mem_percent=latest_mem,
        net_total_mb_s=latest_net,
        cpu_history=[value for _, value in cpu_history],
        mem_history=[value for _, value in mem_history],
        net_history=[value for _, value in net_history],
        top_interfaces=top_interfaces,
    )


def _build_timers_block(payload: Any) -> TimersBlock:
    timers = []
    if isinstance(payload, dict):
        rows = payload.get("timers")
        if isinstance(rows, list):
            timers = [row for row in rows if isinstance(row, dict)]

    total = len(timers)
    running = 0
    paused = 0
    rows_out: list[str] = []

    order = {"running": 0, "paused": 1, "idle": 2, "finished": 3}
    timers_sorted = sorted(
        timers,
        key=lambda row: (
            order.get(str(row.get("state") or "idle"), 9),
            str(row.get("updated_at") or ""),
        ),
    )

    for row in timers_sorted:
        state = str(row.get("state") or "idle").strip().lower()
        kind = str(row.get("kind") or "timer").strip().lower()
        name = str(row.get("name") or "unnamed").strip() or "unnamed"
        if state == "running":
            running += 1
        if state == "paused":
            paused += 1

        elapsed = max(0.0, _safe_float(row.get("elapsed_seconds"), 0.0))
        remaining = row.get("remaining_seconds")
        if kind == "timer":
            if remaining is None:
                value = _fmt_seconds_short(elapsed)
            else:
                value = (
                    f"{_fmt_seconds_short(max(0.0, _safe_float(remaining, 0.0)))} left"
                )
        else:
            value = f"{_fmt_seconds_short(elapsed)} up"

        state_tag = state[:7].upper().ljust(7)
        rows_out.append(f"[{state_tag}] {name} | {value}")

    return TimersBlock(total=total, running=running, paused=paused, rows=rows_out[:8])


def _build_workspaces_block(events: list[dict[str, Any]]) -> WorkspacesBlock:
    pairs: dict[tuple[str, str], int] = {}
    for event in events:
        data = event.get("data")
        if not isinstance(data, dict):
            continue
        if data.get(END_MARKER_KEY) is True:
            continue

        from_ws = (
            str(
                data.get("from_workspace")
                or data.get("prev_workspace")
                or data.get("workspace")
                or "?"
            ).strip()
            or "?"
        )
        to_ws = (
            str(data.get("to_workspace") or data.get("workspace") or "?").strip() or "?"
        )
        key = (from_ws, to_ws)
        pairs[key] = pairs.get(key, 0) + 1

    top_pairs = sorted(
        ((left, right, count) for (left, right), count in pairs.items()),
        key=lambda item: item[2],
        reverse=True,
    )[:6]
    return WorkspacesBlock(switch_count=sum(pairs.values()), top_pairs=top_pairs)


def _build_tabs_block(
    events: list[dict[str, Any]], *, from_dt: datetime, to_dt: datetime
) -> TabsBlock:
    latest_ts: datetime | None = None
    latest_count = 0
    domains: dict[str, float] = {}

    for event in events:
        data = event.get("data")
        if not isinstance(data, dict):
            continue

        ts = _event_point_ts(event)
        if ts is not None:
            count = _safe_int(data.get("count"), 0)
            tabs_raw = data.get("tabs")
            if count <= 0 and isinstance(tabs_raw, list):
                count = len([row for row in tabs_raw if isinstance(row, dict)])
            count = max(0, count)
            if latest_ts is None or ts >= latest_ts:
                latest_ts = ts
                latest_count = count

        tabs_raw = data.get("tabs")
        if not isinstance(tabs_raw, list):
            continue
        tabs = [row for row in tabs_raw if isinstance(row, dict)]
        if not tabs:
            continue

        overlap = _event_overlap_seconds(event, from_dt=from_dt, to_dt=to_dt)
        if overlap <= 0.0:
            continue
        weighted = overlap / float(len(tabs))

        for tab in tabs:
            domain = _domain_from_url(
                str(
                    tab.get("url")
                    or tab.get("pending_url")
                    or tab.get("pendingUrl")
                    or ""
                )
            )
            domains[domain] = domains.get(domain, 0.0) + weighted

    top_domains = sorted(domains.items(), key=lambda item: item[1], reverse=True)[:5]
    return TabsBlock(latest_count=latest_count, top_domains=top_domains)


def _build_battery_block(events: list[dict[str, Any]]) -> BatteryBlock | None:
    latest_ts: datetime | None = None
    latest_data: dict[str, Any] | None = None

    for event in events:
        data = event.get("data")
        if not isinstance(data, dict):
            continue
        ts = _event_point_ts(event)
        if ts is None:
            continue
        if latest_ts is None or ts >= latest_ts:
            latest_ts = ts
            latest_data = data

    if latest_data is None:
        return None

    capacity = latest_data.get("capacity_percent")
    capacity_value = _safe_float(capacity, default=float("nan"))
    if math.isnan(capacity_value):
        capacity_value = None

    mains_raw = latest_data.get("mains_online")
    mains_online: bool | None
    if isinstance(mains_raw, bool):
        mains_online = mains_raw
    else:
        mains_online = None

    return BatteryBlock(
        available=bool(latest_data.get("available", True)),
        capacity_percent=capacity_value,
        status=str(latest_data.get("status") or "unknown"),
        mains_online=mains_online,
    )


def _fetch_snapshot(
    server_url: str, *, range_key: str, day_window_mode: str
) -> DashboardSnapshot:
    errors: list[str] = []
    client = ActiveWatcherClient(server_url, timeout_seconds=4.0)
    try:
        try:
            window = _resolve_window(
                client, range_key=range_key, day_window_mode=day_window_mode
            )
        except Exception as e:
            now = utcnow()
            errors.append(f"window: {e}")
            window = TimeWindow(
                from_ts=to_rfc3339(now - timedelta(hours=24)),
                to_ts=to_rfc3339(now),
            )

        from_dt = _parse_ts(window.from_ts) or (utcnow() - timedelta(hours=24))
        to_dt = _parse_ts(window.to_ts) or utcnow()

        chunk_seconds = _pick_chunk_seconds(
            range_key, from_ts=window.from_ts, to_ts=window.to_ts
        )
        common_params = {"from": window.from_ts, "to": window.to_ts}
        event_windows = _split_window_for_events(window)

        summary_payload: Any
        try:
            summary_payload = client.get_json(
                "/v1/summary",
                params={
                    **common_params,
                    "chunk_seconds": chunk_seconds,
                    "include_timeline": "false",
                },
            )
        except Exception as e:
            errors.append(f"summary: {e}")
            summary_payload = {}

        def load_events(bucket: str) -> list[dict[str, Any]]:
            rows: list[dict[str, Any]] = []
            seen: set[str] = set()
            for chunk in event_windows:
                try:
                    payload = client.get_json(
                        "/v1/events",
                        params={
                            "from": chunk.from_ts,
                            "to": chunk.to_ts,
                            "bucket": bucket,
                        },
                    )
                except Exception as e:
                    errors.append(f"{bucket}: {e}")
                    continue

                for row in _events_payload_to_rows(payload):
                    key = _event_dedupe_key(row)
                    if key in seen:
                        continue
                    seen.add(key)
                    rows.append(row)

            rows.sort(
                key=lambda row: (
                    str(row.get("start_ts") or ""),
                    str(row.get("end_ts") or ""),
                )
            )
            return rows

        system_events = load_events("system")
        workspace_switch_events = load_events("workspace_switch")
        tabs_events = load_events("browser_tabs")
        battery_events = load_events("battery")

        timers_payload: Any
        try:
            timers_payload = client.get_json("/v1/timers")
        except Exception as e:
            errors.append(f"timers: {e}")
            timers_payload = {}

        return DashboardSnapshot(
            fetched_at=utcnow(),
            window=window,
            range_key=range_key,
            day_window_mode=day_window_mode,
            activity=_build_activity_block(summary_payload),
            system=_build_system_block(system_events, from_dt=from_dt, to_dt=to_dt),
            timers=_build_timers_block(timers_payload),
            workspaces=_build_workspaces_block(workspace_switch_events),
            tabs=_build_tabs_block(tabs_events, from_dt=from_dt, to_dt=to_dt),
            battery=_build_battery_block(battery_events),
            errors=errors,
        )
    finally:
        client.close()


def _safe_addstr(win: curses.window, y: int, x: int, text: str, attr: int = 0) -> None:
    h, w = win.getmaxyx()
    if y < 0 or y >= h:
        return
    if x >= w - 1:
        return
    max_len = max(0, w - 1 - x)
    if max_len <= 0:
        return
    try:
        win.addnstr(y, x, str(text), max_len, attr)
    except curses.error:
        return


def _pair(pair_id: int, *, bold: bool = False, dim: bool = False) -> int:
    attr = curses.color_pair(pair_id)
    if bold:
        attr |= curses.A_BOLD
    if dim:
        attr |= curses.A_DIM
    return attr


def _init_colors() -> None:
    if not curses.has_colors():
        return
    curses.start_color()
    try:
        curses.use_default_colors()
    except curses.error:
        pass

    curses.init_pair(1, curses.COLOR_CYAN, -1)
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_GREEN, -1)
    curses.init_pair(4, curses.COLOR_YELLOW, -1)
    curses.init_pair(5, curses.COLOR_RED, -1)
    curses.init_pair(6, curses.COLOR_MAGENTA, -1)
    curses.init_pair(7, curses.COLOR_WHITE, -1)


def _draw_box(
    stdscr: curses.window, y: int, x: int, h: int, w: int, title: str
) -> curses.window | None:
    if h < 3 or w < 8:
        return None
    try:
        win = stdscr.derwin(h, w, y, x)
    except curses.error:
        return None
    win.erase()
    win.attrset(_pair(1))
    try:
        win.box()
    except curses.error:
        return None
    _safe_addstr(win, 0, 2, f" {title} ", _pair(2, bold=True))
    return win


def _render_header(
    stdscr: curses.window,
    *,
    snapshot: DashboardSnapshot | None,
    last_error: str,
    refresh_seconds: float,
    show_help: bool,
) -> None:
    h, w = stdscr.getmaxyx()
    range_key = snapshot.range_key if snapshot is not None else "?"
    mode = snapshot.day_window_mode if snapshot is not None else "?"
    status = "OK"
    status_attr = _pair(3, bold=True)

    error_count = 0
    if snapshot is not None:
        error_count = len(snapshot.errors)
    if last_error:
        error_count += 1
    if error_count > 0:
        status = f"WARN {error_count}"
        status_attr = _pair(4, bold=True)

    title = "ACTIVEWATCHER TUI  ::  btop-style"
    _safe_addstr(stdscr, 0, 1, _trim(title, max(0, w - 2)), _pair(2, bold=True))
    _safe_addstr(stdscr, 0, max(1, w - 16), _trim(status, 14), status_attr)

    fetched = "-"
    if snapshot is not None:
        fetched = snapshot.fetched_at.astimezone().strftime("%H:%M:%S")
    line = f"range={range_key} day-window={mode} refresh={refresh_seconds:.1f}s updated={fetched}"
    _safe_addstr(stdscr, 1, 1, _trim(line, max(0, w - 2)), _pair(7, dim=True))

    keys = "keys: q quit | r refresh | 1 24h | 2 1w | 3 1m | 4 all | m mode | h help"
    _safe_addstr(stdscr, 2, 1, _trim(keys, max(0, w - 2)), _pair(7, dim=not show_help))


def _render_activity_panel(win: curses.window, snapshot: DashboardSnapshot) -> None:
    h, w = win.getmaxyx()
    inner_w = max(1, w - 2)

    from_text = snapshot.window.from_ts.replace("T", " ").replace("Z", " UTC")
    to_text = snapshot.window.to_ts.replace("T", " ").replace("Z", " UTC")
    _safe_addstr(win, 1, 1, _trim(f"window: {from_text}", inner_w), _pair(7, dim=True))
    _safe_addstr(win, 2, 1, _trim(f"to:     {to_text}", inner_w), _pair(7, dim=True))

    total = max(0.0, snapshot.activity.total_seconds)
    rows = [
        ("active", snapshot.activity.active_seconds, _pair(3, bold=True)),
        ("afk   ", snapshot.activity.afk_seconds, _pair(4, bold=True)),
        ("off   ", snapshot.activity.off_seconds, _pair(5, bold=True)),
    ]

    bar_w = max(8, min(40, inner_w - 24))
    y = 4
    for label, value, attr in rows:
        if y >= h - 2:
            break
        pct = (value / total * 100.0) if total > 0 else 0.0
        bar = render_bar(value, total, bar_w)
        line = f"{label} [{bar}] {pct:5.1f}%"
        _safe_addstr(win, y, 1, _trim(line, inner_w), attr)
        y += 1

    if y < h - 1:
        total_line = f"total: {_fmt_seconds_short(total)}"
        _safe_addstr(win, y, 1, _trim(total_line, inner_w), _pair(6, bold=True))


def _render_top_apps_panel(win: curses.window, snapshot: DashboardSnapshot) -> None:
    h, w = win.getmaxyx()
    inner_w = max(1, w - 2)
    rows = snapshot.activity.top_apps
    if not rows:
        _safe_addstr(
            win, 1, 1, "No app activity in selected window.", _pair(7, dim=True)
        )
        return

    y = 1
    for idx, (name, seconds) in enumerate(rows, start=1):
        if y >= h - 1:
            break
        left = _trim(f"{idx:>2}. {name}", max(1, inner_w - 10))
        right = _fmt_seconds_short(seconds)
        line = f"{left} {right.rjust(max(0, inner_w - len(left) - 1))}"
        _safe_addstr(win, y, 1, _trim(line, inner_w), _pair(6))
        y += 1


def _render_system_panel(win: curses.window, snapshot: DashboardSnapshot) -> None:
    h, w = win.getmaxyx()
    inner_w = max(1, w - 2)
    sys = snapshot.system

    _safe_addstr(
        win,
        1,
        1,
        _trim(
            f"CPU {sys.cpu_percent:5.1f}% | RAM {sys.mem_percent:5.1f}% | NET {sys.net_total_mb_s:6.2f} MB/s",
            inner_w,
        ),
        _pair(6, bold=True),
    )

    spark_w = max(8, inner_w - 12)
    cpu_sp = render_sparkline(sys.cpu_history[-120:], spark_w)
    mem_sp = render_sparkline(sys.mem_history[-120:], spark_w)
    net_sp = render_sparkline(sys.net_history[-120:], spark_w)

    _safe_addstr(win, 3, 1, _trim(f"CPU {cpu_sp}", inner_w), _pair(3))
    _safe_addstr(win, 4, 1, _trim(f"RAM {mem_sp}", inner_w), _pair(4))
    _safe_addstr(win, 5, 1, _trim(f"NET {net_sp}", inner_w), _pair(1))

    if sys.top_interfaces:
        iface_text = ", ".join(
            f"{name}:{_fmt_seconds_short(seconds)}"
            for name, seconds in sys.top_interfaces
        )
        _safe_addstr(
            win, 7, 1, _trim(f"ifaces {iface_text}", inner_w), _pair(7, dim=True)
        )
    else:
        _safe_addstr(win, 7, 1, _trim("ifaces -", inner_w), _pair(7, dim=True))


def _render_timers_panel(win: curses.window, snapshot: DashboardSnapshot) -> None:
    h, w = win.getmaxyx()
    inner_w = max(1, w - 2)
    timers = snapshot.timers
    _safe_addstr(
        win,
        1,
        1,
        _trim(
            f"total={timers.total} running={timers.running} paused={timers.paused}",
            inner_w,
        ),
        _pair(6, bold=True),
    )

    if not timers.rows:
        _safe_addstr(win, 3, 1, "No timers available.", _pair(7, dim=True))
        return

    y = 3
    for row in timers.rows:
        if y >= h - 1:
            break
        _safe_addstr(win, y, 1, _trim(row, inner_w), _pair(2))
        y += 1


def _render_workspace_panel(win: curses.window, snapshot: DashboardSnapshot) -> None:
    h, w = win.getmaxyx()
    inner_w = max(1, w - 2)
    ws = snapshot.workspaces

    _safe_addstr(
        win,
        1,
        1,
        _trim(f"switches: {ws.switch_count}", inner_w),
        _pair(6, bold=True),
    )

    if not ws.top_pairs:
        _safe_addstr(win, 3, 1, "No workspace switch data.", _pair(7, dim=True))
        return

    y = 3
    for left, right, count in ws.top_pairs:
        if y >= h - 1:
            break
        _safe_addstr(win, y, 1, _trim(f"{left} -> {right}: {count}", inner_w), _pair(1))
        y += 1


def _render_tabs_battery_panel(win: curses.window, snapshot: DashboardSnapshot) -> None:
    h, w = win.getmaxyx()
    inner_w = max(1, w - 2)
    tabs = snapshot.tabs

    _safe_addstr(
        win,
        1,
        1,
        _trim(f"tabs open: {tabs.latest_count}", inner_w),
        _pair(6, bold=True),
    )

    if tabs.top_domains:
        domains_text = ", ".join(
            f"{domain}:{_fmt_seconds_short(seconds)}"
            for domain, seconds in tabs.top_domains
        )
        _safe_addstr(
            win, 2, 1, _trim(f"top domains: {domains_text}", inner_w), _pair(2)
        )
    else:
        _safe_addstr(win, 2, 1, _trim("top domains: -", inner_w), _pair(7, dim=True))

    battery = snapshot.battery
    if battery is None:
        _safe_addstr(
            win, 4, 1, _trim("battery: no samples", inner_w), _pair(7, dim=True)
        )
    elif not battery.available:
        _safe_addstr(
            win, 4, 1, _trim("battery: unavailable", inner_w), _pair(7, dim=True)
        )
    else:
        cap = "-"
        if battery.capacity_percent is not None:
            cap = f"{battery.capacity_percent:5.1f}%"
        mains = "mains:?"
        if battery.mains_online is True:
            mains = "mains:on"
        elif battery.mains_online is False:
            mains = "mains:off"
        line = f"battery: {cap} {battery.status} {mains}"
        _safe_addstr(win, 4, 1, _trim(line, inner_w), _pair(4, bold=True))

    if snapshot.errors:
        first = "; ".join(snapshot.errors[:2])
        _safe_addstr(win, h - 2, 1, _trim(f"errors: {first}", inner_w), _pair(5))


def _render_help_overlay(stdscr: curses.window) -> None:
    h, w = stdscr.getmaxyx()
    box_h = min(12, max(8, h - 4))
    box_w = min(70, max(40, w - 4))
    y = max(1, (h - box_h) // 2)
    x = max(1, (w - box_w) // 2)
    win = _draw_box(stdscr, y, x, box_h, box_w, "HELP")
    if win is None:
        return

    lines = [
        "q      quit",
        "r      refresh now",
        "1      range 24h",
        "2      range 1w",
        "3      range 1m",
        "4      range all",
        "m      toggle day-window (midnight/rolling)",
        "h      toggle this help",
    ]
    y_line = 1
    for line in lines:
        if y_line >= box_h - 1:
            break
        _safe_addstr(win, y_line, 2, _trim(line, box_w - 4), _pair(7))
        y_line += 1


def _render(
    stdscr: curses.window,
    *,
    snapshot: DashboardSnapshot | None,
    last_error: str,
    refresh_seconds: float,
    show_help: bool,
) -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    _render_header(
        stdscr,
        snapshot=snapshot,
        last_error=last_error,
        refresh_seconds=refresh_seconds,
        show_help=show_help,
    )

    if h < 20 or w < 90:
        msg = "Terminal too small for dashboard layout (need at least 90x20)."
        _safe_addstr(stdscr, 5, 2, _trim(msg, max(0, w - 4)), _pair(5, bold=True))
        stdscr.noutrefresh()
        curses.doupdate()
        return

    if snapshot is None:
        if last_error:
            _safe_addstr(
                stdscr,
                5,
                2,
                _trim(
                    f"Waiting for first snapshot (error: {last_error})", max(0, w - 4)
                ),
                _pair(5, bold=True),
            )
        else:
            _safe_addstr(
                stdscr,
                5,
                2,
                _trim("Waiting for first snapshot...", max(0, w - 4)),
                _pair(7, dim=True),
            )
        stdscr.noutrefresh()
        curses.doupdate()
        return

    body_y = 3
    body_h = h - body_y
    left_w = max(40, min(w - 40, int(w * 0.48)))
    right_w = w - left_w

    top_h = max(8, body_h // 3)
    mid_h = max(8, body_h // 3)
    bottom_h = body_h - top_h - mid_h
    if bottom_h < 6:
        deficit = 6 - bottom_h
        cut_mid = min(deficit, max(0, mid_h - 8))
        mid_h -= cut_mid
        deficit -= cut_mid
        cut_top = min(deficit, max(0, top_h - 8))
        top_h -= cut_top
        bottom_h = body_h - top_h - mid_h

    p_activity = _draw_box(stdscr, body_y, 0, top_h, left_w, "ACTIVITY")
    p_apps = _draw_box(stdscr, body_y + top_h, 0, mid_h, left_w, "TOP APPS")
    p_ws = _draw_box(stdscr, body_y + top_h + mid_h, 0, bottom_h, left_w, "WORKSPACES")

    p_system = _draw_box(stdscr, body_y, left_w, top_h, right_w, "SYSTEM")
    p_timers = _draw_box(stdscr, body_y + top_h, left_w, mid_h, right_w, "TIMERS")
    p_tabs = _draw_box(
        stdscr, body_y + top_h + mid_h, left_w, bottom_h, right_w, "TABS / BATTERY"
    )

    if p_activity is not None:
        _render_activity_panel(p_activity, snapshot)
        p_activity.noutrefresh()
    if p_apps is not None:
        _render_top_apps_panel(p_apps, snapshot)
        p_apps.noutrefresh()
    if p_ws is not None:
        _render_workspace_panel(p_ws, snapshot)
        p_ws.noutrefresh()
    if p_system is not None:
        _render_system_panel(p_system, snapshot)
        p_system.noutrefresh()
    if p_timers is not None:
        _render_timers_panel(p_timers, snapshot)
        p_timers.noutrefresh()
    if p_tabs is not None:
        _render_tabs_battery_panel(p_tabs, snapshot)
        p_tabs.noutrefresh()

    if show_help:
        _render_help_overlay(stdscr)

    stdscr.noutrefresh()
    curses.doupdate()


def _run_loop(
    stdscr: curses.window,
    *,
    server_url: str,
    refresh_seconds: float,
    initial_range: str,
    initial_day_window_mode: str,
) -> None:
    try:
        curses.curs_set(0)
    except curses.error:
        pass
    stdscr.nodelay(True)
    stdscr.keypad(True)
    _init_colors()

    range_key = initial_range
    day_window_mode = initial_day_window_mode
    show_help = False

    snapshot: DashboardSnapshot | None = None
    last_error = ""
    force_refresh = True
    last_fetch_monotonic = 0.0

    while True:
        now = time.monotonic()
        if force_refresh or (now - last_fetch_monotonic) >= refresh_seconds:
            try:
                snapshot = _fetch_snapshot(
                    server_url,
                    range_key=range_key,
                    day_window_mode=day_window_mode,
                )
                last_error = ""
            except Exception as e:
                last_error = str(e)
            last_fetch_monotonic = now
            force_refresh = False

        _render(
            stdscr,
            snapshot=snapshot,
            last_error=last_error,
            refresh_seconds=refresh_seconds,
            show_help=show_help,
        )

        key = stdscr.getch()
        if key == -1:
            time.sleep(0.05)
            continue

        if key in (ord("q"), ord("Q"), 27):
            return
        if key in (ord("r"), ord("R")):
            force_refresh = True
            continue
        if key == ord("1"):
            range_key = "24h"
            force_refresh = True
            continue
        if key == ord("2"):
            range_key = "1w"
            force_refresh = True
            continue
        if key == ord("3"):
            range_key = "1m"
            force_refresh = True
            continue
        if key == ord("4"):
            range_key = "all"
            force_refresh = True
            continue
        if key in (ord("m"), ord("M")):
            day_window_mode = "rolling" if day_window_mode == "midnight" else "midnight"
            force_refresh = True
            continue
        if key in (ord("h"), ord("H"), ord("?")):
            show_help = not show_help
            continue
        if key == curses.KEY_RESIZE:
            continue


def run_dashboard_tui(
    *,
    server_url: str,
    refresh_seconds: float,
    range_key: str,
    day_window_mode: str,
) -> None:
    normalized_range = normalize_dashboard_range(range_key)
    normalized_day_window = normalize_day_window_mode(day_window_mode)
    refresh = max(0.2, float(refresh_seconds))

    curses.wrapper(
        lambda stdscr: _run_loop(
            stdscr,
            server_url=server_url,
            refresh_seconds=refresh,
            initial_range=normalized_range,
            initial_day_window_mode=normalized_day_window,
        )
    )
