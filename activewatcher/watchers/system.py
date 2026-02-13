from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from activewatcher.common.http import ActiveWatcherAsyncClient


def _canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _read_cpu_sample() -> tuple[int, int]:
    with open("/proc/stat", encoding="utf-8", errors="replace") as f:
        line = f.readline().strip()
    parts = line.split()
    if len(parts) < 6 or parts[0] != "cpu":
        raise RuntimeError("invalid /proc/stat cpu line")
    values = [int(v) for v in parts[1:]]
    total = sum(values)
    idle = values[3] + (values[4] if len(values) > 4 else 0)
    return total, idle


def _read_mem_sample() -> tuple[int, int]:
    mem_total_kb = 0
    mem_available_kb = 0
    with open("/proc/meminfo", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("MemTotal:"):
                fields = line.split()
                if len(fields) >= 2 and fields[1].isdigit():
                    mem_total_kb = int(fields[1])
            elif line.startswith("MemAvailable:"):
                fields = line.split()
                if len(fields) >= 2 and fields[1].isdigit():
                    mem_available_kb = int(fields[1])
            if mem_total_kb > 0 and mem_available_kb > 0:
                break
    if mem_total_kb <= 0:
        raise RuntimeError("could not read MemTotal from /proc/meminfo")
    if mem_available_kb < 0:
        mem_available_kb = 0
    mem_used_kb = max(0, mem_total_kb - mem_available_kb)
    return mem_total_kb * 1024, mem_used_kb * 1024


def _read_network_totals(*, include_loopback: bool) -> tuple[int, int, list[str]]:
    rx_total = 0
    tx_total = 0
    interfaces: list[str] = []
    with open("/proc/net/dev", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    for raw in lines[2:]:
        if ":" not in raw:
            continue
        iface, rest = raw.split(":", 1)
        name = iface.strip()
        if not name:
            continue
        if not include_loopback and name == "lo":
            continue
        cols = rest.split()
        if len(cols) < 16:
            continue
        try:
            rx_bytes = int(cols[0])
            tx_bytes = int(cols[8])
        except ValueError:
            continue
        rx_total += max(0, rx_bytes)
        tx_total += max(0, tx_bytes)
        interfaces.append(name)
    interfaces.sort(key=lambda s: s.lower())
    return rx_total, tx_total, interfaces


@dataclass
class SystemWatcher:
    server_url: str
    source: str
    poll_seconds: float
    heartbeat_seconds: int
    include_loopback: bool

    def __post_init__(self) -> None:
        self._last_sent_state: str | None = None
        self._last_sent_at: float = 0.0
        self._prev_cpu_total: int | None = None
        self._prev_cpu_idle: int | None = None
        self._prev_net_rx: int | None = None
        self._prev_net_tx: int | None = None
        self._prev_net_ts: float | None = None

    async def maybe_send(self, *, data: dict[str, Any], force: bool) -> None:
        now = time.monotonic()
        state_json = _canonical_json(data)
        should_send = force or state_json != self._last_sent_state
        if self.heartbeat_seconds > 0 and (now - self._last_sent_at) >= self.heartbeat_seconds:
            should_send = True
        if not should_send:
            return

        ts = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        payload = {"bucket": "system", "source": self.source, "ts": ts, "data": data}

        client = ActiveWatcherAsyncClient(self.server_url)
        try:
            await client.post_state(payload)
            self._last_sent_state = state_json
            self._last_sent_at = now
        finally:
            await client.aclose()

    async def tick(self) -> None:
        cpu_total, cpu_idle = _read_cpu_sample()
        cpu_percent = 0.0
        if self._prev_cpu_total is not None and self._prev_cpu_idle is not None:
            dt = max(0, cpu_total - self._prev_cpu_total)
            di = max(0, cpu_idle - self._prev_cpu_idle)
            if dt > 0:
                cpu_percent = max(0.0, min(100.0, (1.0 - (di / dt)) * 100.0))
        self._prev_cpu_total = cpu_total
        self._prev_cpu_idle = cpu_idle

        mem_total, mem_used = _read_mem_sample()
        mem_percent = (mem_used / mem_total * 100.0) if mem_total > 0 else 0.0

        now = time.monotonic()
        rx_total, tx_total, ifaces = _read_network_totals(include_loopback=self.include_loopback)
        rx_bps = 0.0
        tx_bps = 0.0
        if (
            self._prev_net_ts is not None
            and self._prev_net_rx is not None
            and self._prev_net_tx is not None
            and now > self._prev_net_ts
        ):
            seconds = now - self._prev_net_ts
            rx_bps = max(0.0, (rx_total - self._prev_net_rx) / seconds)
            tx_bps = max(0.0, (tx_total - self._prev_net_tx) / seconds)
        self._prev_net_rx = rx_total
        self._prev_net_tx = tx_total
        self._prev_net_ts = now

        data = {
            "cpu_percent": round(cpu_percent, 3),
            "mem_total_bytes": mem_total,
            "mem_used_bytes": mem_used,
            "mem_percent": round(mem_percent, 3),
            "net_rx_bps": round(rx_bps, 3),
            "net_tx_bps": round(tx_bps, 3),
            "net_total_bps": round(rx_bps + tx_bps, 3),
            "net_interfaces": ifaces,
        }
        await self.maybe_send(data=data, force=False)


async def run(
    *,
    server_url: str,
    source: str,
    poll_seconds: float,
    heartbeat_seconds: int,
    include_loopback: bool,
) -> None:
    watcher = SystemWatcher(
        server_url=server_url,
        source=source,
        poll_seconds=poll_seconds,
        heartbeat_seconds=heartbeat_seconds,
        include_loopback=include_loopback,
    )
    print(
        f"[system] poll={poll_seconds}s heartbeat={heartbeat_seconds}s include_loopback={include_loopback}"
    )

    while True:
        try:
            await watcher.tick()
        except Exception as e:
            print(f"[system] error: {e}")
        await asyncio.sleep(max(0.2, poll_seconds))
