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


def _insert_event(
    conn: sqlite3.Connection,
    *,
    bucket: str,
    source: str,
    start: datetime,
    end: datetime | None,
    last_seen: datetime,
    data_json: str,
) -> None:
    conn.execute(
        """
        INSERT INTO events(bucket, source, start_ts, end_ts, last_seen_ts, data_json)
        VALUES (?, ?, ?, ?, ?, ?)
        """.strip(),
        (
            bucket,
            source,
            to_rfc3339(start),
            to_rfc3339(end) if end is not None else None,
            to_rfc3339(last_seen),
            data_json,
        ),
    )


class ReportsExtraTests(unittest.TestCase):
    def setUp(self) -> None:
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        db.init_db(self.conn)

    def tearDown(self) -> None:
        self.conn.close()

    def test_merge_ranges_overlap_and_sum(self) -> None:
        ranges = [
            (_dt(0), _dt(30)),
            (_dt(20), _dt(40)),
            (_dt(50), _dt(60)),
            (_dt(60), _dt(70)),
        ]
        merged = reports._merge_ranges(ranges)
        self.assertEqual(merged, [(_dt(0), _dt(40)), (_dt(50), _dt(70))])
        self.assertAlmostEqual(reports._sum_ranges(merged), 60.0, places=3)
        self.assertAlmostEqual(
            reports._sum_overlap(merged, _dt(10), _dt(55)), 35.0, places=3
        )

    def test_list_apps_and_data_range(self) -> None:
        _insert_event(
            self.conn,
            bucket="window",
            source="hyprland",
            start=_dt(0),
            end=_dt(60),
            last_seen=_dt(60),
            data_json='{"app":"Code","title":"main.py"}',
        )
        _insert_event(
            self.conn,
            bucket="window",
            source="hyprland",
            start=_dt(60),
            end=_dt(120),
            last_seen=_dt(120),
            data_json='{"app":"__no_focus__","title":""}',
        )
        _insert_event(
            self.conn,
            bucket="window",
            source="hyprland",
            start=_dt(120),
            end=_dt(180),
            last_seen=_dt(180),
            data_json='{"app":"Firefox","title":"docs"}',
        )
        self.conn.commit()

        apps_payload = reports.list_apps(
            self.conn,
            from_ts=_dt(300),
            to_ts=_dt(0),
            limit=5,
        )
        self.assertEqual(apps_payload["apps"], ["Code", "Firefox"])

        from_dt, to_dt = reports.data_range(
            self.conn, bucket="window", source="hyprland"
        )
        self.assertEqual(to_rfc3339(from_dt), "2026-03-01T12:00:00.000Z")
        self.assertEqual(to_rfc3339(to_dt), "2026-03-01T12:03:00.000Z")

    def test_data_range_invalid_timestamp_returns_empty(self) -> None:
        self.conn.execute(
            """
            INSERT INTO events(bucket, source, start_ts, end_ts, last_seen_ts, data_json)
            VALUES ('window', 'src', 'not-a-ts', 'also-bad', 'still-bad', '{}')
            """.strip()
        )
        self.conn.commit()
        from_dt, to_dt = reports.data_range(self.conn)
        self.assertIsNone(from_dt)
        self.assertIsNone(to_dt)

    def test_heatmap_window_and_active_modes(self) -> None:
        _insert_event(
            self.conn,
            bucket="window",
            source="hyprland",
            start=_dt(0),
            end=_dt(120),
            last_seen=_dt(120),
            data_json='{"app":"Code","title":"file"}',
        )
        _insert_event(
            self.conn,
            bucket="window",
            source="hyprland",
            start=_dt(120),
            end=_dt(240),
            last_seen=_dt(240),
            data_json='{"app":"Firefox","title":"docs"}',
        )
        _insert_event(
            self.conn,
            bucket="idle",
            source="logind",
            start=_dt(0),
            end=_dt(60),
            last_seen=_dt(60),
            data_json='{"afk":false}',
        )
        _insert_event(
            self.conn,
            bucket="idle",
            source="logind",
            start=_dt(60),
            end=_dt(120),
            last_seen=_dt(120),
            data_json='{"afk":true}',
        )
        _insert_event(
            self.conn,
            bucket="idle",
            source="logind",
            start=_dt(120),
            end=_dt(240),
            last_seen=_dt(240),
            data_json='{"afk":false}',
        )
        self.conn.commit()

        window_payload = reports.heatmap(
            self.conn,
            from_ts=_dt(0),
            to_ts=_dt(240),
            tz="UTC",
            mode="window",
            apps=["Code", "Firefox"],
        )
        self.assertEqual(window_payload["mode"], "window")
        self.assertEqual(window_payload["apps"], ["Code", "Firefox"])
        self.assertEqual(len(window_payload["days"]), 1)

        active_payload = reports.heatmap(
            self.conn,
            from_ts=_dt(0),
            to_ts=_dt(240),
            tz="UTC",
            mode="active",
            apps=None,
        )
        self.assertEqual(active_payload["mode"], "active")
        self.assertTrue(active_payload["has_idle"])
        self.assertGreater(active_payload["max_seconds"], 0.0)

        with self.assertRaisesRegex(ValueError, "mode must be one of"):
            reports.heatmap(
                self.conn,
                from_ts=_dt(0),
                to_ts=_dt(10),
                tz="UTC",
                mode="invalid",
                apps=None,
            )

        with self.assertRaisesRegex(ValueError, "unknown timezone"):
            reports.heatmap(
                self.conn,
                from_ts=_dt(0),
                to_ts=_dt(10),
                tz="Mars/Colony",
                mode="window",
                apps=None,
            )

    def test_build_timeline_top_apps_and_chunking(self) -> None:
        windows = [
            reports.Interval(
                id=1,
                bucket="window",
                source="src",
                start=_dt(0),
                end=_dt(30),
                data={"app": "Code", "title": "a"},
            ),
            reports.Interval(
                id=2,
                bucket="window",
                source="src",
                start=_dt(30),
                end=_dt(60),
                data={"app": "Code", "title": "a"},
            ),
            reports.Interval(
                id=3,
                bucket="window",
                source="src",
                start=_dt(60),
                end=_dt(90),
                data={"app": "Firefox", "title": "b"},
            ),
        ]
        idle = [
            reports.Interval(
                id=10,
                bucket="idle",
                source="src",
                start=_dt(20),
                end=_dt(40),
                data={"afk": True},
            ),
            reports.Interval(
                id=11,
                bucket="idle",
                source="src",
                start=_dt(40),
                end=_dt(90),
                data={"afk": False},
            ),
        ]

        timeline = reports.build_timeline(
            from_dt=_dt(0), to_dt=_dt(90), window_intervals=windows, idle_intervals=idle
        )
        self.assertGreaterEqual(len(timeline), 3)
        # ensure merge happened for same app before idle split
        self.assertEqual(timeline[0].window.get("app"), "Code")
        _ = timeline[0].to_json()

        total_rows = reports.top_apps_total(timeline)
        active_rows = reports.top_apps_active(timeline)
        self.assertEqual(total_rows[0]["app"], "Code")
        self.assertTrue(any(row["app"] == "Firefox" for row in active_rows))

        runtime_ranges = reports._merge_ranges([(_dt(0), _dt(90))])
        afk_ranges = reports._merge_ranges([(_dt(20), _dt(40))])
        chunks = reports.chunk_timeline(
            from_dt=_dt(0),
            to_dt=_dt(90),
            segments=timeline,
            runtime_ranges=runtime_ranges,
            afk_ranges=afk_ranges,
            chunk_seconds=30,
        )
        self.assertEqual(len(chunks), 3)
        self.assertIsNone(chunks[0]["top_app"])
        self.assertEqual(chunks[1]["top_app"], "Code")
        self.assertEqual(
            reports.chunk_timeline(
                from_dt=_dt(0),
                to_dt=_dt(90),
                segments=timeline,
                runtime_ranges=runtime_ranges,
                afk_ranges=afk_ranges,
                chunk_seconds=0,
            ),
            [],
        )

    def test_categories_summary_visible_and_auto_modes(self) -> None:
        _insert_event(
            self.conn,
            bucket="window_visible",
            source="hyprland:win:1",
            start=_dt(0),
            end=_dt(120),
            last_seen=_dt(120),
            data_json='{"app":"Code","title":"README"}',
        )
        _insert_event(
            self.conn,
            bucket="window",
            source="hyprland",
            start=_dt(0),
            end=_dt(120),
            last_seen=_dt(120),
            data_json='{"app":"Firefox","title":"docs"}',
        )
        _insert_event(
            self.conn,
            bucket="idle",
            source="logind",
            start=_dt(0),
            end=_dt(120),
            last_seen=_dt(120),
            data_json='{"afk":false}',
        )
        _insert_event(
            self.conn,
            bucket="browser_tabs",
            source="tabs:firefox",
            start=_dt(0),
            end=_dt(120),
            last_seen=_dt(120),
            data_json='{"browser":"Firefox","tabs":[{"url":"https://github.com","title":"PR"}]}',
        )
        self.conn.commit()

        visible = reports.categories_summary(
            self.conn, from_ts=_dt(0), to_ts=_dt(120), mode="visible"
        )
        self.assertEqual(visible["mode"], "visible")
        self.assertGreaterEqual(visible["apps_total_seconds"], 0.0)

        auto = reports.categories_summary(
            self.conn, from_ts=_dt(0), to_ts=_dt(120), mode="auto"
        )
        self.assertEqual(auto["mode"], "active")
        self.assertIn("apps", auto)
        self.assertIn("tabs", auto)

        with self.assertRaisesRegex(ValueError, "mode must be one of"):
            reports.categories_summary(
                self.conn, from_ts=_dt(0), to_ts=_dt(120), mode="invalid"
            )

    def test_domain_rows_and_named_seconds_helpers(self) -> None:
        self.assertEqual(
            reports._tab_domain_from_url("https://www.example.com/path"), "example.com"
        )
        self.assertEqual(reports._tab_domain_from_url("about:config"), "about")
        self.assertEqual(reports._tab_domain_from_url(""), "internal")

        totals: dict[str, dict[str, float]] = {}
        reports._add_cat_named_seconds(totals, category="dev", name="", seconds=10.0)
        self.assertEqual(totals, {})
        reports._add_cat_named_seconds(
            totals, category="dev", name="Code", seconds=12.0
        )
        self.assertEqual(totals["dev"]["Code"], 12.0)

        class _EmptyCatalog:
            rules: list = []

            @staticmethod
            def category_meta() -> list[dict[str, str]]:
                return []

        rows, total_seconds = reports._category_rows(_EmptyCatalog(), {})
        self.assertEqual(total_seconds, 0.0)
        self.assertEqual(len(rows), 1)


if __name__ == "__main__":
    unittest.main()
