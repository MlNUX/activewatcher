from __future__ import annotations

import sqlite3
import unittest
from datetime import datetime, timedelta, timezone
from typing import Any

from activewatcher.server import db, timers


def _utc(second_offset: int = 0) -> datetime:
    base = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
    return base + timedelta(seconds=second_offset)


def _as_int(value: Any) -> int:
    try:
        return int(value)
    except Exception:
        return 0


def _as_float(value: Any) -> float:
    try:
        return float(value)
    except Exception:
        return 0.0


def _timer_by_id(rows: list[dict[str, object]], timer_id: int) -> dict[str, object]:
    for row in rows:
        if _as_int(row.get("id")) == timer_id:
            return row
    raise AssertionError(f"timer id not found in payload: {timer_id}")


class TimersApiLogicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        db.init_db(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def test_create_timer_requires_duration(self) -> None:
        with self.assertRaisesRegex(timers.TimerValidationError, "duration_seconds"):
            timers.create_timer(self.conn, name="focus", kind="timer", now=_utc(0))

    def test_counter_stop_archives_elapsed_and_reactivate_preserves_elapsed(
        self,
    ) -> None:
        created = timers.create_timer(
            self.conn, name="pomodoros", kind="counter", now=_utc(0)
        )
        timer_id = int(created["id"])

        started = timers.start_timer(self.conn, timer_id=timer_id, now=_utc(0))
        self.assertEqual(started.get("state"), "running")

        paused = timers.pause_timer(self.conn, timer_id=timer_id, now=_utc(42))
        self.assertEqual(paused.get("state"), "paused")
        self.assertAlmostEqual(_as_float(paused.get("elapsed_seconds")), 42.0, places=3)

        timers.start_timer(self.conn, timer_id=timer_id, now=_utc(45))
        listed = timers.list_timers(self.conn, now=_utc(50))
        row = _timer_by_id(listed.get("timers") or [], timer_id)
        self.assertEqual(row.get("state"), "running")
        self.assertAlmostEqual(_as_float(row.get("elapsed_seconds")), 47.0, places=3)

        stopped = timers.stop_timer(self.conn, timer_id=timer_id, now=_utc(60))
        self.assertEqual(stopped.get("state"), "idle")
        self.assertAlmostEqual(
            _as_float(stopped.get("elapsed_seconds")), 57.0, places=3
        )

        reactivated = timers.reactivate_timer(
            self.conn, timer_id=timer_id, now=_utc(61)
        )
        self.assertEqual(reactivated.get("state"), "paused")
        self.assertAlmostEqual(
            _as_float(reactivated.get("elapsed_seconds")), 57.0, places=3
        )

    def test_timer_finishes_and_start_restarts_from_full_duration(self) -> None:
        created = timers.create_timer(
            self.conn,
            name="deep work",
            kind="timer",
            duration_seconds=5,
            now=_utc(0),
        )
        timer_id = int(created["id"])

        timers.start_timer(self.conn, timer_id=timer_id, now=_utc(0))

        listed_finished = timers.list_timers(self.conn, now=_utc(8))
        finished = _timer_by_id(listed_finished.get("timers") or [], timer_id)
        self.assertEqual(finished.get("state"), "finished")
        self.assertAlmostEqual(
            _as_float(finished.get("remaining_seconds")), 0.0, places=3
        )

        restarted = timers.start_timer(self.conn, timer_id=timer_id, now=_utc(10))
        self.assertEqual(restarted.get("state"), "running")
        self.assertAlmostEqual(
            _as_float(restarted.get("elapsed_seconds")), 0.0, places=3
        )
        self.assertAlmostEqual(
            _as_float(restarted.get("remaining_seconds")), 5.0, places=3
        )

        listed_running = timers.list_timers(self.conn, now=_utc(12))
        running = _timer_by_id(listed_running.get("timers") or [], timer_id)
        self.assertEqual(running.get("state"), "running")
        self.assertAlmostEqual(
            _as_float(running.get("remaining_seconds")), 3.0, places=3
        )

        stopped = timers.stop_timer(self.conn, timer_id=timer_id, now=_utc(13))
        self.assertEqual(stopped.get("state"), "idle")
        self.assertAlmostEqual(_as_float(stopped.get("elapsed_seconds")), 3.0, places=3)
        self.assertAlmostEqual(
            _as_float(stopped.get("remaining_seconds")), 2.0, places=3
        )

        reactivated = timers.reactivate_timer(
            self.conn, timer_id=timer_id, now=_utc(14)
        )
        self.assertEqual(reactivated.get("state"), "paused")
        self.assertAlmostEqual(
            _as_float(reactivated.get("elapsed_seconds")), 3.0, places=3
        )
        self.assertAlmostEqual(
            _as_float(reactivated.get("remaining_seconds")), 2.0, places=3
        )

    def test_delete_timer_removes_row_and_future_lookups_fail(self) -> None:
        created = timers.create_timer(
            self.conn, name="archive me", kind="counter", now=_utc(0)
        )
        timer_id = int(created["id"])

        timers.start_timer(self.conn, timer_id=timer_id, now=_utc(0))
        timers.stop_timer(self.conn, timer_id=timer_id, now=_utc(9))

        deleted = timers.delete_timer(self.conn, timer_id=timer_id, now=_utc(10))
        self.assertEqual(_as_int(deleted.get("id")), timer_id)
        self.assertEqual(deleted.get("name"), "archive me")

        listed = timers.list_timers(self.conn, now=_utc(11))
        self.assertEqual(len(listed.get("timers") or []), 0)

        with self.assertRaises(timers.TimerNotFoundError):
            timers.delete_timer(self.conn, timer_id=timer_id, now=_utc(12))


if __name__ == "__main__":
    unittest.main()
