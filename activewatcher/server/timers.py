from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from activewatcher.common.time import parse_rfc3339, to_rfc3339, to_utc, utcnow


TimerKind = Literal["timer", "counter"]
TimerState = Literal["idle", "running", "paused", "finished"]

_VALID_KINDS: set[str] = {"timer", "counter"}
_VALID_STATES: set[str] = {"idle", "running", "paused", "finished"}
_MAX_NAME_LENGTH = 120
_MAX_DURATION_SECONDS = 7 * 24 * 3600


class TimerValidationError(ValueError):
    pass


class TimerNotFoundError(FileNotFoundError):
    pass


@dataclass(frozen=True)
class TimerSnapshot:
    id: int
    name: str
    kind: TimerKind
    state: TimerState
    duration_seconds: int
    elapsed_seconds: float
    remaining_seconds: float | None
    created_at: str
    updated_at: str

    def to_json(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "state": self.state,
            "duration_seconds": self.duration_seconds,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "remaining_seconds": (
                round(self.remaining_seconds, 3)
                if self.remaining_seconds is not None
                else None
            ),
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


def _coerce_now(now: datetime | None) -> datetime:
    return to_utc(now) if now is not None else utcnow()


def _normalize_name(value: Any) -> str:
    name = str(value or "").strip()
    if not name:
        raise TimerValidationError("name is required")
    if len(name) > _MAX_NAME_LENGTH:
        raise TimerValidationError(f"name too long (max {_MAX_NAME_LENGTH} characters)")
    return name


def _normalize_kind(value: Any) -> TimerKind:
    kind = str(value or "").strip().lower()
    if kind not in _VALID_KINDS:
        raise TimerValidationError("kind must be one of: timer, counter")
    return kind  # type: ignore[return-value]


def _normalize_duration_seconds(kind: TimerKind, value: Any) -> int:
    if kind == "counter":
        return 0

    if value is None:
        raise TimerValidationError("duration_seconds is required for timer")

    try:
        seconds = int(value)
    except Exception as e:  # pragma: no cover - defensive
        raise TimerValidationError("duration_seconds must be an integer") from e

    if seconds < 1 or seconds > _MAX_DURATION_SECONDS:
        raise TimerValidationError(
            f"duration_seconds must be between 1 and {_MAX_DURATION_SECONDS}"
        )
    return seconds


def _normalize_state(value: Any) -> TimerState:
    state = str(value or "idle").strip().lower()
    if state not in _VALID_STATES:
        return "idle"
    return state  # type: ignore[return-value]


def _safe_running_extra_seconds(
    *, state: TimerState, running_since_raw: Any, now: datetime
) -> float:
    if state != "running" or running_since_raw is None:
        return 0.0
    try:
        started = to_utc(parse_rfc3339(str(running_since_raw)))
    except Exception:
        return 0.0
    return max(0.0, (now - started).total_seconds())


def _snapshot_from_row(row: sqlite3.Row, *, now: datetime) -> TimerSnapshot:
    timer_id = int(row["id"])
    name = str(row["name"] or "")
    kind = _normalize_kind(row["kind"])
    state = _normalize_state(row["state"])
    duration_seconds = max(0, int(row["duration_seconds"] or 0))
    elapsed_base = max(0.0, float(row["elapsed_seconds"] or 0.0))
    elapsed = elapsed_base + _safe_running_extra_seconds(
        state=state, running_since_raw=row["running_since_ts"], now=now
    )

    remaining_seconds: float | None = None
    effective_state = state
    if kind == "timer":
        total = float(duration_seconds)
        remaining_seconds = max(0.0, total - elapsed)
        if remaining_seconds <= 0:
            elapsed = total
            effective_state = "finished"

    return TimerSnapshot(
        id=timer_id,
        name=name,
        kind=kind,
        state=effective_state,
        duration_seconds=duration_seconds,
        elapsed_seconds=elapsed,
        remaining_seconds=remaining_seconds,
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _should_persist_finished_timer(
    *, row: sqlite3.Row, snapshot: TimerSnapshot
) -> bool:
    if snapshot.kind != "timer" or snapshot.state != "finished":
        return False
    stored_state = _normalize_state(row["state"])
    stored_running_since = row["running_since_ts"]
    try:
        stored_elapsed = max(0.0, float(row["elapsed_seconds"] or 0.0))
    except Exception:  # pragma: no cover - defensive
        stored_elapsed = 0.0
    return (
        stored_state != "finished"
        or stored_running_since is not None
        or abs(stored_elapsed - float(snapshot.duration_seconds)) > 1e-6
    )


def _persist_finished_timer(
    conn: sqlite3.Connection, *, timer_id: int, duration_seconds: int, now_iso: str
) -> None:
    conn.execute(
        """
        UPDATE timers
           SET elapsed_seconds = ?,
               running_since_ts = NULL,
               state = 'finished',
               updated_at = ?
         WHERE id = ?
        """.strip(),
        (float(max(0, int(duration_seconds))), now_iso, int(timer_id)),
    )


def _fetch_timer_row(conn: sqlite3.Connection, timer_id: int) -> sqlite3.Row:
    row = conn.execute(
        """
        SELECT
          id,
          name,
          kind,
          duration_seconds,
          elapsed_seconds,
          running_since_ts,
          state,
          created_at,
          updated_at
          FROM timers
         WHERE id = ?
         LIMIT 1
        """.strip(),
        (int(timer_id),),
    ).fetchone()
    if row is None:
        raise TimerNotFoundError(f"timer not found: {timer_id}")
    return row


def list_timers(
    conn: sqlite3.Connection, *, now: datetime | None = None
) -> dict[str, Any]:
    instant = _coerce_now(now)
    now_iso = to_rfc3339(instant)
    rows = conn.execute(
        """
        SELECT
          id,
          name,
          kind,
          duration_seconds,
          elapsed_seconds,
          running_since_ts,
          state,
          created_at,
          updated_at
          FROM timers
         ORDER BY created_at DESC, id DESC
        """.strip()
    ).fetchall()

    snapshots: list[TimerSnapshot] = []
    finished_to_persist: list[tuple[int, int]] = []
    for row in rows:
        snapshot = _snapshot_from_row(row, now=instant)
        snapshots.append(snapshot)
        if _should_persist_finished_timer(row=row, snapshot=snapshot):
            finished_to_persist.append((snapshot.id, snapshot.duration_seconds))

    if finished_to_persist:
        conn.execute("BEGIN IMMEDIATE")
        try:
            for timer_id, duration_seconds in finished_to_persist:
                _persist_finished_timer(
                    conn,
                    timer_id=timer_id,
                    duration_seconds=duration_seconds,
                    now_iso=now_iso,
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise

    return {
        "server_ts": now_iso,
        "timers": [snapshot.to_json() for snapshot in snapshots],
    }


def create_timer(
    conn: sqlite3.Connection,
    *,
    name: Any,
    kind: Any,
    duration_seconds: Any = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    timer_name = _normalize_name(name)
    timer_kind = _normalize_kind(kind)
    timer_duration = _normalize_duration_seconds(timer_kind, duration_seconds)
    instant = _coerce_now(now)
    now_iso = to_rfc3339(instant)

    conn.execute("BEGIN IMMEDIATE")
    try:
        cur = conn.execute(
            """
            INSERT INTO timers(
              name,
              kind,
              duration_seconds,
              elapsed_seconds,
              running_since_ts,
              state,
              created_at,
              updated_at
            )
            VALUES (?, ?, ?, 0, NULL, 'idle', ?, ?)
            """.strip(),
            (timer_name, timer_kind, timer_duration, now_iso, now_iso),
        )
        lastrowid = cur.lastrowid
        if lastrowid is None:  # pragma: no cover - sqlite defensive guard
            raise RuntimeError("failed to create timer")
        row = _fetch_timer_row(conn, int(lastrowid))
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise
    return _snapshot_from_row(row, now=instant).to_json()


def start_timer(
    conn: sqlite3.Connection, *, timer_id: int, now: datetime | None = None
) -> dict[str, Any]:
    instant = _coerce_now(now)
    now_iso = to_rfc3339(instant)

    conn.execute("BEGIN IMMEDIATE")
    try:
        row = _fetch_timer_row(conn, timer_id)
        current = _snapshot_from_row(row, now=instant)
        if current.state == "running":
            conn.execute("COMMIT")
            return current.to_json()

        next_elapsed = (
            0.0
            if current.kind == "timer" and current.state == "finished"
            else current.elapsed_seconds
        )
        conn.execute(
            """
            UPDATE timers
               SET elapsed_seconds = ?,
                   running_since_ts = ?,
                   state = 'running',
                   updated_at = ?
             WHERE id = ?
            """.strip(),
            (next_elapsed, now_iso, now_iso, timer_id),
        )
        updated = _fetch_timer_row(conn, timer_id)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    return _snapshot_from_row(updated, now=instant).to_json()


def pause_timer(
    conn: sqlite3.Connection, *, timer_id: int, now: datetime | None = None
) -> dict[str, Any]:
    instant = _coerce_now(now)
    now_iso = to_rfc3339(instant)

    conn.execute("BEGIN IMMEDIATE")
    try:
        row = _fetch_timer_row(conn, timer_id)
        current = _snapshot_from_row(row, now=instant)
        if current.state != "running":
            if _should_persist_finished_timer(row=row, snapshot=current):
                _persist_finished_timer(
                    conn,
                    timer_id=current.id,
                    duration_seconds=current.duration_seconds,
                    now_iso=now_iso,
                )
                row = _fetch_timer_row(conn, timer_id)
                current = _snapshot_from_row(row, now=instant)
            conn.execute("COMMIT")
            return current.to_json()

        next_state: TimerState = "paused"
        next_elapsed = current.elapsed_seconds
        if (
            current.kind == "timer"
            and current.remaining_seconds is not None
            and current.remaining_seconds <= 0
        ):
            next_state = "finished"
            next_elapsed = float(current.duration_seconds)

        conn.execute(
            """
            UPDATE timers
               SET elapsed_seconds = ?,
                   running_since_ts = NULL,
                   state = ?,
                   updated_at = ?
             WHERE id = ?
            """.strip(),
            (next_elapsed, next_state, now_iso, timer_id),
        )
        updated = _fetch_timer_row(conn, timer_id)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    return _snapshot_from_row(updated, now=instant).to_json()


def stop_timer(
    conn: sqlite3.Connection, *, timer_id: int, now: datetime | None = None
) -> dict[str, Any]:
    instant = _coerce_now(now)
    now_iso = to_rfc3339(instant)

    conn.execute("BEGIN IMMEDIATE")
    try:
        row = _fetch_timer_row(conn, timer_id)
        current = _snapshot_from_row(row, now=instant)
        next_elapsed = current.elapsed_seconds
        if (
            current.kind == "timer"
            and current.remaining_seconds is not None
            and current.remaining_seconds <= 0
        ):
            next_elapsed = float(current.duration_seconds)

        conn.execute(
            """
            UPDATE timers
               SET elapsed_seconds = ?,
                    running_since_ts = NULL,
                    state = 'idle',
                    updated_at = ?
              WHERE id = ?
            """.strip(),
            (next_elapsed, now_iso, timer_id),
        )
        updated = _fetch_timer_row(conn, timer_id)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    return _snapshot_from_row(updated, now=instant).to_json()


def delete_timer(
    conn: sqlite3.Connection, *, timer_id: int, now: datetime | None = None
) -> dict[str, Any]:
    instant = _coerce_now(now)

    conn.execute("BEGIN IMMEDIATE")
    try:
        row = _fetch_timer_row(conn, timer_id)
        snapshot = _snapshot_from_row(row, now=instant)
        conn.execute(
            """
            DELETE FROM timers
             WHERE id = ?
            """.strip(),
            (timer_id,),
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    return snapshot.to_json()


def reactivate_timer(
    conn: sqlite3.Connection, *, timer_id: int, now: datetime | None = None
) -> dict[str, Any]:
    instant = _coerce_now(now)
    now_iso = to_rfc3339(instant)

    conn.execute("BEGIN IMMEDIATE")
    try:
        row = _fetch_timer_row(conn, timer_id)
        current = _snapshot_from_row(row, now=instant)
        next_elapsed = current.elapsed_seconds
        next_state: TimerState = "paused" if next_elapsed > 0 else "idle"
        if current.kind == "timer" and current.state == "finished":
            next_elapsed = 0.0
            next_state = "idle"

        conn.execute(
            """
            UPDATE timers
               SET elapsed_seconds = ?,
                    running_since_ts = NULL,
                    state = ?,
                    updated_at = ?
              WHERE id = ?
            """.strip(),
            (next_elapsed, next_state, now_iso, timer_id),
        )
        updated = _fetch_timer_row(conn, timer_id)
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    return _snapshot_from_row(updated, now=instant).to_json()
