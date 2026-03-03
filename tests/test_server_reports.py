from __future__ import annotations

import sqlite3
import unittest
from datetime import datetime, timedelta, timezone

from activewatcher.common.categories import category_catalog
from activewatcher.common.time import to_rfc3339
from activewatcher.server import db, reports


def _dt(offset_seconds: int) -> datetime:
    base = datetime(2026, 3, 1, 12, 0, 0, tzinfo=timezone.utc)
    return base + timedelta(seconds=offset_seconds)


class ReportsLogicTests(unittest.TestCase):
    def test_load_ranges_matches_load_intervals_time_spans(self) -> None:
        conn = sqlite3.connect(":memory:", check_same_thread=False)
        conn.row_factory = sqlite3.Row
        db.init_db(conn)

        rows = [
            {
                "bucket": "window",
                "source": "s1",
                "start": _dt(-60),
                "end": _dt(120),
                "last_seen": _dt(120),
            },
            {
                "bucket": "system",
                "source": "s2",
                "start": _dt(120),
                "end": None,
                "last_seen": _dt(240),
            },
            {
                "bucket": "browser_tabs",
                "source": "s3",
                "start": _dt(510),
                "end": None,
                "last_seen": _dt(570),
            },
            {
                "bucket": "workspace",
                "source": "s4",
                "start": _dt(720),
                "end": _dt(780),
                "last_seen": _dt(780),
            },
        ]

        for row in rows:
            conn.execute(
                """
                INSERT INTO events(bucket, source, start_ts, end_ts, last_seen_ts, data_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """.strip(),
                (
                    row["bucket"],
                    row["source"],
                    to_rfc3339(row["start"]),
                    to_rfc3339(row["end"]) if row["end"] is not None else None,
                    to_rfc3339(row["last_seen"]),
                    "{}",
                ),
            )
        conn.commit()

        from_ts = _dt(0)
        to_ts = _dt(600)

        _, _, intervals = reports.load_intervals(
            conn, bucket=None, source=None, from_ts=from_ts, to_ts=to_ts
        )
        _, _, ranges = reports._load_ranges(
            conn, bucket=None, source=None, from_ts=from_ts, to_ts=to_ts
        )

        expected = sorted([(it.start, it.end) for it in intervals], key=lambda r: r[0])
        actual = sorted(ranges, key=lambda r: r[0])
        self.assertEqual(actual, expected)

        conn.close()

    def test_app_category_stats_from_segments_match_existing_helpers(self) -> None:
        catalog = category_catalog()
        segments = [
            reports.TimelineSegment(
                start=_dt(0),
                end=_dt(60),
                window={"app": "Code", "title": "main.py"},
                afk=False,
            ),
            reports.TimelineSegment(
                start=_dt(60),
                end=_dt(120),
                window={"app": "Code", "title": "main.py"},
                afk=False,
            ),
            reports.TimelineSegment(
                start=_dt(120),
                end=_dt(180),
                window={"app": "Slack", "title": "DM"},
                afk=True,
            ),
            reports.TimelineSegment(
                start=_dt(180), end=_dt(210), window=None, afk=None
            ),
        ]

        totals_old = reports._app_category_totals_from_segments(
            catalog, segments, only_active=False
        )
        details_old = reports._app_category_details_from_segments(
            catalog, segments, only_active=False
        )
        totals_new, details_new = reports._app_category_stats_from_segments(
            catalog, segments, only_active=False
        )
        self.assertEqual(totals_new, totals_old)
        self.assertEqual(details_new, details_old)

        totals_old_active = reports._app_category_totals_from_segments(
            catalog, segments, only_active=True
        )
        details_old_active = reports._app_category_details_from_segments(
            catalog, segments, only_active=True
        )
        totals_new_active, details_new_active = (
            reports._app_category_stats_from_segments(
                catalog, segments, only_active=True
            )
        )
        self.assertEqual(totals_new_active, totals_old_active)
        self.assertEqual(details_new_active, details_old_active)

    def test_app_category_stats_from_intervals_match_existing_helpers(self) -> None:
        catalog = category_catalog()
        intervals = [
            reports.Interval(
                id=1,
                bucket="window_visible",
                source="src",
                start=_dt(0),
                end=_dt(60),
                data={"app": "Code", "title": "readme.md"},
            ),
            reports.Interval(
                id=2,
                bucket="window_visible",
                source="src",
                start=_dt(60),
                end=_dt(150),
                data={"app": "Firefox", "title": "github.com"},
            ),
            reports.Interval(
                id=3,
                bucket="window_visible",
                source="src",
                start=_dt(150),
                end=_dt(150),
                data={"app": "Code", "title": "zero"},
            ),
        ]

        totals_old = reports._app_category_totals_from_intervals(catalog, intervals)
        details_old = reports._app_category_details_from_intervals(catalog, intervals)
        totals_new, details_new = reports._app_category_stats_from_intervals(
            catalog, intervals
        )
        self.assertEqual(totals_new, totals_old)
        self.assertEqual(details_new, details_old)

    def test_tabs_category_stats_match_existing_helpers(self) -> None:
        catalog = category_catalog()
        intervals = [
            reports.Interval(
                id=1,
                bucket="browser_tabs",
                source="",
                start=_dt(0),
                end=_dt(120),
                data={
                    "tabs": [
                        {"url": "https://github.com/", "title": "PR"},
                        {"url": "https://mail.google.com", "title": "Inbox"},
                    ]
                },
            ),
            reports.Interval(
                id=2,
                bucket="browser_tabs",
                source="firefox",
                start=_dt(120),
                end=_dt(180),
                data={
                    "browser": "Firefox",
                    "tabs": [
                        {"url": "https://github.com/", "title": "PR"},
                        {"pending_url": "about:config", "title": "config"},
                        "not-a-dict",
                    ],
                },
            ),
        ]

        totals_old = reports._tabs_category_totals(catalog, intervals)
        details_old = reports._tabs_category_details(catalog, intervals)
        totals_new, details_new = reports._tabs_category_stats(catalog, intervals)

        self.assertEqual(totals_new, totals_old)
        self.assertEqual(details_new, details_old)


if __name__ == "__main__":
    unittest.main()
