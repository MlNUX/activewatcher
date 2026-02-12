from __future__ import annotations

import json
import sqlite3
from dataclasses import asdict, dataclass
from typing import Literal

from activewatcher.common.models import END_MARKER_KEY, StateEvent
from activewatcher.common.time import to_rfc3339


class NonMonotonicTimestampError(ValueError):
    pass


@dataclass(frozen=True)
class IngestResult:
    action: Literal["inserted", "refreshed", "rotated", "ended", "ended_noop"]
    previous_event_id: int | None
    current_event_id: int | None

    def to_json(self) -> dict:
        return asdict(self)


def _canonical_json(data: dict) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def ingest_state(conn: sqlite3.Connection, state: StateEvent) -> IngestResult:
    bucket = state.bucket
    source = state.source
    ts = to_rfc3339(state.ts)
    end_requested = state.data.get(END_MARKER_KEY) is True
    data = dict(state.data)
    data.pop(END_MARKER_KEY, None)
    data_json = _canonical_json(data)

    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute(
            """
            SELECT id, start_ts, last_seen_ts, data_json
              FROM events
             WHERE bucket = ? AND source = ? AND end_ts IS NULL
             LIMIT 1
            """.strip(),
            (bucket, source),
        ).fetchone()

        if end_requested:
            if row is None:
                conn.execute("COMMIT")
                return IngestResult(action="ended_noop", previous_event_id=None, current_event_id=None)

            event_id = int(row["id"])
            last_seen_ts = str(row["last_seen_ts"])
            start_ts = str(row["start_ts"])

            if ts < last_seen_ts:
                raise NonMonotonicTimestampError(
                    f"non-monotonic ts for end ({bucket},{source}): {ts} < {last_seen_ts}"
                )
            if ts < start_ts:
                raise NonMonotonicTimestampError(
                    f"non-monotonic ts for end ({bucket},{source}): {ts} < {start_ts}"
                )

            conn.execute("UPDATE events SET end_ts = ?, last_seen_ts = ? WHERE id = ?", (ts, ts, event_id))
            conn.execute("COMMIT")
            return IngestResult(action="ended", previous_event_id=event_id, current_event_id=None)

        if row is None:
            cur = conn.execute(
                """
                INSERT INTO events(bucket, source, start_ts, end_ts, last_seen_ts, data_json)
                VALUES (?, ?, ?, NULL, ?, ?)
                """.strip(),
                (bucket, source, ts, ts, data_json),
            )
            event_id = int(cur.lastrowid)
            conn.execute("COMMIT")
            return IngestResult(action="inserted", previous_event_id=None, current_event_id=event_id)

        event_id = int(row["id"])
        last_seen_ts = str(row["last_seen_ts"])
        start_ts = str(row["start_ts"])

        if str(row["data_json"]) == data_json:
            if ts > last_seen_ts:
                conn.execute("UPDATE events SET last_seen_ts = ? WHERE id = ?", (ts, event_id))
            conn.execute("COMMIT")
            return IngestResult(action="refreshed", previous_event_id=event_id, current_event_id=event_id)

        if ts <= last_seen_ts:
            raise NonMonotonicTimestampError(
                f"non-monotonic ts for ({bucket},{source}): {ts} <= {last_seen_ts}"
            )
        if ts <= start_ts:
            raise NonMonotonicTimestampError(
                f"non-monotonic ts for ({bucket},{source}): {ts} <= {start_ts}"
            )

        conn.execute(
            "UPDATE events SET end_ts = ?, last_seen_ts = ? WHERE id = ?",
            (ts, ts, event_id),
        )
        cur = conn.execute(
            """
            INSERT INTO events(bucket, source, start_ts, end_ts, last_seen_ts, data_json)
            VALUES (?, ?, ?, NULL, ?, ?)
            """.strip(),
            (bucket, source, ts, ts, data_json),
        )
        new_id = int(cur.lastrowid)
        conn.execute("COMMIT")
        return IngestResult(action="rotated", previous_event_id=event_id, current_event_id=new_id)
    except Exception:
        conn.execute("ROLLBACK")
        raise
