from __future__ import annotations

import unittest

from activewatcher.cli.dashboard_tui import (
    TimeWindow,
    _split_window_for_events,
    normalize_dashboard_range,
    normalize_day_window_mode,
    render_bar,
    render_sparkline,
)


class DashboardTuiHelpersTests(unittest.TestCase):
    def test_normalize_dashboard_range(self) -> None:
        self.assertEqual(normalize_dashboard_range("24h"), "24h")
        self.assertEqual(normalize_dashboard_range("1W"), "1w")
        self.assertEqual(normalize_dashboard_range(" all "), "all")

        with self.assertRaises(ValueError):
            normalize_dashboard_range("12h")

    def test_normalize_day_window_mode(self) -> None:
        self.assertEqual(normalize_day_window_mode("midnight"), "midnight")
        self.assertEqual(normalize_day_window_mode("ROLLING"), "rolling")

        with self.assertRaises(ValueError):
            normalize_day_window_mode("daily")

    def test_render_bar(self) -> None:
        self.assertEqual(render_bar(0, 10, 8), "--------")
        self.assertEqual(render_bar(5, 10, 8), "####----")
        self.assertEqual(render_bar(10, 10, 8), "########")
        self.assertEqual(render_bar(3, 0, 6), "------")

    def test_render_sparkline(self) -> None:
        line = render_sparkline([0, 1, 3, 6, 10, 7, 4, 1], 20)
        self.assertEqual(len(line), 20)

        empty_line = render_sparkline([], 12)
        self.assertEqual(empty_line, "." * 12)

    def test_split_window_for_events_chunks_long_range(self) -> None:
        window = TimeWindow(
            from_ts="2026-01-01T00:00:00Z", to_ts="2026-02-01T00:00:00Z"
        )
        chunks = _split_window_for_events(window)
        self.assertGreater(len(chunks), 1)
        self.assertEqual(chunks[0].from_ts, "2026-01-01T00:00:00.000Z")
        self.assertEqual(chunks[-1].to_ts, "2026-02-01T00:00:00.000Z")

    def test_split_window_for_events_invalid_range_returns_original(self) -> None:
        window = TimeWindow(from_ts="bad", to_ts="still-bad")
        chunks = _split_window_for_events(window)
        self.assertEqual(chunks, [window])


if __name__ == "__main__":
    unittest.main()
