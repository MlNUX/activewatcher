from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from activewatcher.common.http import ActiveWatcherAsyncClient

POWER_SUPPLY_ROOT = Path("/sys/class/power_supply")


def _canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _read_text(path: Path) -> str | None:
    try:
        value = path.read_text(encoding="utf-8", errors="replace").strip()
    except OSError:
        return None
    if not value:
        return None
    return value


def _read_int(path: Path) -> int | None:
    value = _read_text(path)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _read_micro_as_base(path: Path) -> float | None:
    value = _read_int(path)
    if value is None:
        return None
    return round(value / 1_000_000.0, 6)


def _read_temp_c(path: Path) -> float | None:
    value = _read_int(path)
    if value is None:
        return None
    return round(value / 10.0, 3)


def _compact(data: dict[str, Any]) -> dict[str, Any]:
    compacted: dict[str, Any] = {}
    for key, value in data.items():
        if value is None:
            continue
        if isinstance(value, dict):
            nested = _compact(value)
            if nested:
                compacted[key] = nested
            continue
        if isinstance(value, list):
            if value:
                compacted[key] = value
            continue
        compacted[key] = value
    return compacted


def _supply_dirs() -> list[Path]:
    try:
        entries = [entry for entry in POWER_SUPPLY_ROOT.iterdir() if entry.is_dir()]
    except OSError:
        return []
    entries.sort(key=lambda p: p.name.lower())
    return entries


def _battery_dirs() -> list[Path]:
    batteries: list[Path] = []
    for path in _supply_dirs():
        supply_type = (_read_text(path / "type") or "").lower()
        if supply_type == "battery":
            batteries.append(path)
    return batteries


def _mains_online() -> bool | None:
    states: list[bool] = []
    for path in _supply_dirs():
        supply_type = (_read_text(path / "type") or "").lower()
        online = _read_int(path / "online")
        if online is None:
            continue
        if supply_type in {"mains", "usb", "usb-c", "usb_pd", "wireless"}:
            states.append(online != 0)
    if not states:
        return None
    return any(states)


def _read_battery(path: Path) -> dict[str, Any]:
    status = _read_text(path / "status")
    status_norm = (status or "").lower()

    capacity = _read_int(path / "capacity")
    energy_now_wh = _read_micro_as_base(path / "energy_now")
    energy_full_wh = _read_micro_as_base(path / "energy_full")
    if capacity is None and energy_now_wh is not None and energy_full_wh is not None and energy_full_wh > 0:
        capacity = int(round((energy_now_wh / energy_full_wh) * 100.0))
    if capacity is not None:
        capacity = max(0, min(100, capacity))

    present_raw = _read_int(path / "present")

    data = {
        "name": path.name,
        "status": status,
        "capacity_percent": float(capacity) if capacity is not None else None,
        "is_charging": status_norm == "charging" if status else None,
        "is_discharging": status_norm == "discharging" if status else None,
        "is_full": status_norm == "full" if status else None,
        "present": (present_raw != 0) if present_raw is not None else None,
        "voltage_v": _read_micro_as_base(path / "voltage_now"),
        "current_a": _read_micro_as_base(path / "current_now"),
        "power_w": _read_micro_as_base(path / "power_now"),
        "energy_now_wh": energy_now_wh,
        "energy_full_wh": energy_full_wh,
        "energy_full_design_wh": _read_micro_as_base(path / "energy_full_design"),
        "charge_now_ah": _read_micro_as_base(path / "charge_now"),
        "charge_full_ah": _read_micro_as_base(path / "charge_full"),
        "charge_full_design_ah": _read_micro_as_base(path / "charge_full_design"),
        "technology": _read_text(path / "technology"),
        "cycle_count": _read_int(path / "cycle_count"),
        "temperature_c": _read_temp_c(path / "temp"),
        "time_to_empty_seconds": _read_int(path / "time_to_empty_now"),
        "time_to_full_seconds": _read_int(path / "time_to_full_now"),
    }
    return _compact(data)


def _aggregate_capacity_percent(batteries: list[dict[str, Any]]) -> float | None:
    total_now = 0.0
    total_full = 0.0
    has_energy_samples = False
    for battery in batteries:
        now = battery.get("energy_now_wh")
        full = battery.get("energy_full_wh")
        if isinstance(now, (int, float)) and isinstance(full, (int, float)) and full > 0:
            total_now += float(now)
            total_full += float(full)
            has_energy_samples = True
    if has_energy_samples and total_full > 0:
        return round((total_now / total_full) * 100.0, 3)

    capacity_values: list[float] = []
    for battery in batteries:
        capacity = battery.get("capacity_percent")
        if isinstance(capacity, (int, float)):
            capacity_values.append(float(capacity))
    if not capacity_values:
        return None
    return round(sum(capacity_values) / len(capacity_values), 3)


def _collect_snapshot() -> dict[str, Any]:
    batteries = [_read_battery(path) for path in _battery_dirs()]
    mains_online = _mains_online()
    if not batteries:
        payload = {
            "available": False,
            "battery_count": 0,
            "mains_online": mains_online,
        }
        return _compact(payload)

    statuses = [status for status in (battery.get("status") for battery in batteries) if isinstance(status, str)]
    has_status = bool(statuses)
    payload = {
        "available": True,
        "battery_count": len(batteries),
        "capacity_percent": _aggregate_capacity_percent(batteries),
        "status": statuses[0] if statuses else None,
        "statuses": statuses if len(statuses) > 1 else None,
        "is_charging": any(battery.get("is_charging") is True for battery in batteries) if has_status else None,
        "is_discharging": any(battery.get("is_discharging") is True for battery in batteries) if has_status else None,
        "mains_online": mains_online,
        "batteries": batteries,
    }
    return _compact(payload)


@dataclass
class BatteryWatcher:
    server_url: str
    source: str
    poll_seconds: float
    heartbeat_seconds: int

    def __post_init__(self) -> None:
        self._last_sent_state: str | None = None
        self._last_sent_at: float = 0.0

    async def maybe_send(self, *, data: dict[str, Any], force: bool) -> None:
        now = time.monotonic()
        state_json = _canonical_json(data)
        should_send = force or state_json != self._last_sent_state
        if self.heartbeat_seconds > 0 and (now - self._last_sent_at) >= self.heartbeat_seconds:
            should_send = True
        if not should_send:
            return

        ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        payload = {"bucket": "battery", "source": self.source, "ts": ts, "data": data}

        client = ActiveWatcherAsyncClient(self.server_url)
        try:
            await client.post_state(payload)
            self._last_sent_state = state_json
            self._last_sent_at = now
        finally:
            await client.aclose()

    async def tick(self) -> None:
        data = _collect_snapshot()
        await self.maybe_send(data=data, force=False)


async def run(
    *,
    server_url: str,
    source: str,
    poll_seconds: float,
    heartbeat_seconds: int,
) -> None:
    watcher = BatteryWatcher(
        server_url=server_url,
        source=source,
        poll_seconds=poll_seconds,
        heartbeat_seconds=heartbeat_seconds,
    )
    print(f"[battery] poll={poll_seconds}s heartbeat={heartbeat_seconds}s")

    while True:
        try:
            await watcher.tick()
        except Exception as e:
            print(f"[battery] error: {e}")
        await asyncio.sleep(max(0.2, poll_seconds))
