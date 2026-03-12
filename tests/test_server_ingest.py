from __future__ import annotations

import sqlite3
import unittest
from datetime import datetime, timedelta, timezone
from unittest import mock

from activewatcher.common.models import END_MARKER_KEY, StateEvent
from activewatcher.server import db, ingest


def _dt(offset_seconds: int) -> datetime:
    base = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
    return base + timedelta(seconds=offset_seconds)


def _state(
    *, ts: datetime, data: dict, bucket: str = "window", source: str = "src"
) -> StateEvent:
    return StateEvent(bucket=bucket, source=source, ts=ts, data=data)


class IngestLogicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        db.init_db(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def test_insert_refresh_rotate_flow(self) -> None:
        inserted = ingest.ingest_state(
            self.conn, _state(ts=_dt(0), data={"app": "Code", "title": "a"})
        )
        self.assertEqual(inserted.action, "inserted")
        self.assertIsNone(inserted.previous_event_id)
        self.assertIsNotNone(inserted.current_event_id)

        refreshed = ingest.ingest_state(
            self.conn, _state(ts=_dt(10), data={"app": "Code", "title": "a"})
        )
        self.assertEqual(refreshed.action, "refreshed")
        self.assertEqual(refreshed.previous_event_id, inserted.current_event_id)
        self.assertEqual(refreshed.current_event_id, inserted.current_event_id)

        rotated = ingest.ingest_state(
            self.conn, _state(ts=_dt(20), data={"app": "Firefox", "title": "b"})
        )
        self.assertEqual(rotated.action, "rotated")
        self.assertEqual(rotated.previous_event_id, inserted.current_event_id)
        self.assertNotEqual(rotated.current_event_id, inserted.current_event_id)

        rows = self.conn.execute(
            "SELECT id, start_ts, end_ts, last_seen_ts FROM events ORDER BY id ASC"
        ).fetchall()
        self.assertEqual(len(rows), 2)
        self.assertEqual(str(rows[0]["end_ts"]), "2026-03-01T12:00:20.000Z")
        self.assertIsNone(rows[1]["end_ts"])

    def test_end_marker_variants(self) -> None:
        noop = ingest.ingest_state(
            self.conn,
            _state(
                ts=_dt(0), data={END_MARKER_KEY: True}, bucket="idle", source="logind"
            ),
        )
        self.assertEqual(noop.action, "ended_noop")
        self.assertIsNone(noop.current_event_id)

        inserted = ingest.ingest_state(
            self.conn,
            _state(ts=_dt(1), data={"afk": False}, bucket="idle", source="logind"),
        )
        ended = ingest.ingest_state(
            self.conn,
            _state(
                ts=_dt(5), data={END_MARKER_KEY: True}, bucket="idle", source="logind"
            ),
        )
        self.assertEqual(ended.action, "ended")
        self.assertEqual(ended.previous_event_id, inserted.current_event_id)
        self.assertIsNone(ended.current_event_id)

        row = self.conn.execute(
            "SELECT end_ts, last_seen_ts FROM events WHERE id = ?",
            (inserted.current_event_id,),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(str(row["end_ts"]), "2026-03-01T12:00:05.000Z")
        self.assertEqual(str(row["last_seen_ts"]), "2026-03-01T12:00:05.000Z")

    def test_non_monotonic_rotation_raises_and_rolls_back(self) -> None:
        ingest.ingest_state(self.conn, _state(ts=_dt(0), data={"app": "Code"}))
        ingest.ingest_state(self.conn, _state(ts=_dt(30), data={"app": "Code"}))

        with self.assertRaises(ingest.NonMonotonicTimestampError):
            ingest.ingest_state(self.conn, _state(ts=_dt(20), data={"app": "Firefox"}))

        rows = self.conn.execute(
            "SELECT id, end_ts, last_seen_ts, data_json FROM events ORDER BY id"
        ).fetchall()
        self.assertEqual(len(rows), 1)
        self.assertIsNone(rows[0]["end_ts"])
        self.assertEqual(str(rows[0]["last_seen_ts"]), "2026-03-01T12:00:30.000Z")
        self.assertIn("Code", str(rows[0]["data_json"]))

    def test_non_monotonic_end_raises(self) -> None:
        ingest.ingest_state(
            self.conn, _state(ts=_dt(10), data={"afk": False}, bucket="idle")
        )
        with self.assertRaises(ingest.NonMonotonicTimestampError):
            ingest.ingest_state(
                self.conn,
                _state(ts=_dt(9), data={END_MARKER_KEY: True}, bucket="idle"),
            )

    def test_stale_gap_rotates_at_last_seen(self) -> None:
        with mock.patch(
            "activewatcher.server.ingest.default_stale_after_seconds", return_value=5
        ):
            inserted = ingest.ingest_state(
                self.conn, _state(ts=_dt(0), data={"app": "Code", "title": "a"})
            )
            ingest.ingest_state(
                self.conn, _state(ts=_dt(2), data={"app": "Code", "title": "a"})
            )
            rotated = ingest.ingest_state(
                self.conn, _state(ts=_dt(20), data={"app": "Firefox", "title": "b"})
            )

        self.assertEqual(rotated.action, "rotated")
        self.assertEqual(rotated.previous_event_id, inserted.current_event_id)

        prev_row = self.conn.execute(
            "SELECT end_ts, last_seen_ts FROM events WHERE id = ?",
            (inserted.current_event_id,),
        ).fetchone()
        self.assertIsNotNone(prev_row)
        self.assertEqual(str(prev_row["end_ts"]), "2026-03-01T12:00:02.000Z")
        self.assertEqual(str(prev_row["last_seen_ts"]), "2026-03-01T12:00:02.000Z")


if __name__ == "__main__":
    unittest.main()
