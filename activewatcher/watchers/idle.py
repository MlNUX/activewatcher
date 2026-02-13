from __future__ import annotations

import asyncio
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from activewatcher.common.http import ActiveWatcherAsyncClient


def _canonical_json(data: dict[str, Any]) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


async def _run(cmd: list[str]) -> str:
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    out, err = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed: {err.decode('utf-8', 'replace').strip()}")
    return out.decode("utf-8", "replace")


async def _get_session_id() -> str:
    env = os.environ.get("XDG_SESSION_ID")
    if env:
        return env

    uid = os.getuid()
    out = await _run(["loginctl", "list-sessions", "--no-legend"])
    candidates: list[str] = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 3:
            continue
        session_id, uid_s, _user = parts[0], parts[1], parts[2]
        if uid_s.isdigit() and int(uid_s) == uid:
            candidates.append(session_id)
    if not candidates:
        raise RuntimeError("could not determine XDG_SESSION_ID (no loginctl sessions for current uid)")
    return candidates[-1]


async def _read_idle_props(session_id: str) -> dict[str, str]:
    out = await _run(
        [
            "loginctl",
            "show-session",
            session_id,
            "-p",
            "LockedHint",
            "-p",
            "IdleHint",
            "-p",
            "IdleSinceHint",
            "-p",
            "IdleSinceHintMonotonic",
        ]
    )
    props: dict[str, str] = {}
    for line in out.splitlines():
        if "=" not in line:
            continue
        k, v = line.split("=", 1)
        props[k.strip()] = v.strip()
    return props


def _truthy(value: str) -> bool:
    return value.strip().lower() in ("yes", "true", "1")


@dataclass(frozen=True)
class AfkDecision:
    afk: bool
    # Preferred start timestamp for this state. Used to backfill AFK over suspend gaps.
    transition_ts: datetime | None


def _idle_since_wallclock(props: dict[str, str]) -> datetime | None:
    since_us_s = props.get("IdleSinceHint", "")
    if not since_us_s.isdigit():
        return None
    since_us = int(since_us_s)
    if since_us <= 0:
        return None
    try:
        return datetime.fromtimestamp(since_us / 1_000_000.0, tz=timezone.utc)
    except (OverflowError, OSError, ValueError):
        return None


def _read_proc_comm(pid: int) -> str | None:
    try:
        with open(f"/proc/{pid}/comm", encoding="utf-8", errors="replace") as f:
            return f.readline().strip()
    except OSError:
        return None


def _find_proc_by_comm(comm: str) -> int | None:
    if not comm:
        return None
    try:
        with os.scandir("/proc") as it:
            for entry in it:
                if not entry.name.isdigit():
                    continue
                pid = int(entry.name)
                if _read_proc_comm(pid) == comm:
                    return pid
    except OSError:
        return None
    return None


@dataclass
class ProcessRunningCache:
    comm: str
    pid: int | None = None

    def is_running(self) -> bool:
        if not self.comm:
            return False
        if self.pid is not None and _read_proc_comm(self.pid) == self.comm:
            return True
        self.pid = _find_proc_by_comm(self.comm)
        return self.pid is not None


def _compute_afk(
    *,
    props: dict[str, str],
    threshold_seconds: int,
    force_afk: bool,
    now_utc: datetime,
) -> AfkDecision:
    if force_afk:
        return AfkDecision(afk=True, transition_ts=now_utc)

    locked_hint = _truthy(props.get("LockedHint", ""))
    if locked_hint:
        return AfkDecision(afk=True, transition_ts=now_utc)

    idle_hint = _truthy(props.get("IdleHint", ""))
    if not idle_hint:
        return AfkDecision(afk=False, transition_ts=None)

    threshold = max(0, threshold_seconds)

    since_wall = _idle_since_wallclock(props)
    if since_wall is not None:
        idle_seconds = max(0.0, (now_utc - since_wall).total_seconds())
        if idle_seconds >= threshold:
            transition = since_wall + timedelta(seconds=threshold)
            if transition > now_utc:
                transition = now_utc
            return AfkDecision(afk=True, transition_ts=transition)
        return AfkDecision(afk=False, transition_ts=None)

    since_us_s = props.get("IdleSinceHintMonotonic", "")
    if since_us_s.isdigit():
        since_us = int(since_us_s)
        now_us = time.monotonic_ns() // 1000
        idle_seconds = max(0.0, (now_us - since_us) / 1_000_000.0)
        if idle_seconds >= threshold:
            return AfkDecision(afk=True, transition_ts=now_utc)
        return AfkDecision(afk=False, transition_ts=None)

    return AfkDecision(afk=True, transition_ts=now_utc)


@dataclass
class IdleWatcher:
    server_url: str
    source: str
    threshold_seconds: int
    poll_seconds: float
    heartbeat_seconds: int

    def __post_init__(self) -> None:
        self._last_sent_state: str | None = None
        self._last_sent_at: float = 0.0
        self._last_sent_ts_utc: datetime | None = None

    async def maybe_send(
        self,
        *,
        afk: bool,
        session_id: str,
        force: bool,
        ts: datetime | None = None,
    ) -> None:
        now = time.monotonic()
        data = {"afk": afk, "threshold_seconds": self.threshold_seconds, "session_id": session_id}
        state_json = _canonical_json(data)

        should_send = force or state_json != self._last_sent_state
        if self.heartbeat_seconds > 0 and (now - self._last_sent_at) >= self.heartbeat_seconds:
            should_send = True
        if not should_send:
            return

        ts_dt = ts.astimezone(timezone.utc) if ts is not None else datetime.now(timezone.utc)
        now_dt = datetime.now(timezone.utc)
        if self._last_sent_ts_utc is not None and ts_dt <= self._last_sent_ts_utc:
            bumped = self._last_sent_ts_utc + timedelta(milliseconds=1)
            ts_dt = bumped if bumped <= now_dt else now_dt
        if ts_dt > now_dt:
            ts_dt = now_dt
        ts_iso = ts_dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")
        payload = {"bucket": "idle", "source": self.source, "ts": ts_iso, "data": data}
        backfill_refresh_needed = afk and ts_dt < (now_dt - timedelta(seconds=1))

        client = ActiveWatcherAsyncClient(self.server_url)
        try:
            await client.post_state(payload)
            if backfill_refresh_needed:
                # When AFK start is backdated (e.g., after suspend), immediately refresh at "now"
                # so the open interval stays alive and is not clipped by stale timeout.
                refresh_now = datetime.now(timezone.utc)
                refresh_ts_dt = refresh_now if refresh_now > ts_dt else (ts_dt + timedelta(milliseconds=1))
                refresh_iso = refresh_ts_dt.isoformat(timespec="milliseconds").replace("+00:00", "Z")
                refresh_payload = {
                    "bucket": "idle",
                    "source": self.source,
                    "ts": refresh_iso,
                    "data": data,
                }
                await client.post_state(refresh_payload)
                ts_dt = refresh_ts_dt
            self._last_sent_state = state_json
            self._last_sent_at = time.monotonic()
            self._last_sent_ts_utc = ts_dt
        finally:
            await client.aclose()


async def run(
    *,
    server_url: str,
    source: str,
    threshold_seconds: int,
    poll_seconds: float,
    heartbeat_seconds: int,
    lock_process: str,
) -> None:
    session_id = await _get_session_id()
    watcher = IdleWatcher(
        server_url=server_url,
        source=source,
        threshold_seconds=threshold_seconds,
        poll_seconds=poll_seconds,
        heartbeat_seconds=heartbeat_seconds,
    )
    lock_proc = ProcessRunningCache(lock_process)
    print(f"[idle] session={session_id} threshold={threshold_seconds}s poll={poll_seconds}s")

    while True:
        try:
            now_utc = datetime.now(timezone.utc)
            props = await _read_idle_props(session_id)
            force_afk = lock_proc.is_running()
            decision = _compute_afk(
                props=props,
                threshold_seconds=threshold_seconds,
                force_afk=force_afk,
                now_utc=now_utc,
            )
            await watcher.maybe_send(
                afk=decision.afk,
                session_id=session_id,
                force=False,
                ts=decision.transition_ts or now_utc,
            )
        except Exception as e:
            print(f"[idle] error: {e}")
        await asyncio.sleep(max(0.2, poll_seconds))
