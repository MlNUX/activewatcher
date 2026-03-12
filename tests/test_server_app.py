from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from activewatcher.server import app as server_app


def _state_payload(
    *,
    ts: str,
    bucket: str = "window",
    source: str = "hyprland",
    data: dict | None = None,
) -> dict:
    return {
        "bucket": bucket,
        "source": source,
        "ts": ts,
        "data": data or {},
    }


class AppHelpersTests(unittest.TestCase):
    def test_normalize_origin(self) -> None:
        self.assertEqual(
            server_app._normalize_origin("http://localhost:5173"),
            "http://localhost:5173",
        )
        self.assertEqual(
            server_app._normalize_origin("https://127.0.0.1:8712/"),
            "https://127.0.0.1:8712",
        )
        self.assertEqual(server_app._normalize_origin("*"), "*")
        self.assertIsNone(server_app._normalize_origin("file:///tmp/test"))
        self.assertIsNone(server_app._normalize_origin("http://localhost:5173/path"))
        self.assertIsNone(server_app._normalize_origin("http://localhost:5173/?a=1"))

    def test_cors_and_trusted_host_helpers(self) -> None:
        with mock.patch(
            "activewatcher.server.app.app_config.config_str_list",
            side_effect=[
                ["http://localhost:5173", "http://localhost:5173", "bad://origin", ""],
                [" ", "127.0.0.1", "localhost"],
            ],
        ):
            cors = server_app._cors_allow_origins()
            trusted = server_app._trusted_hosts()

        self.assertEqual(cors, ["http://localhost:5173"])
        self.assertEqual(trusted, ["127.0.0.1", "localhost"])

        with mock.patch(
            "activewatcher.server.app.app_config.config_str_list",
            side_effect=[[], []],
        ):
            self.assertIn("http://127.0.0.1:5173", server_app._cors_allow_origins())
            self.assertEqual(
                server_app._trusted_hosts(), ["127.0.0.1", "localhost", "[::1]"]
            )

    def test_frontend_dist_dir_and_parse_dt_param(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            custom = Path(tmp) / "frontend-dist"
            with mock.patch.dict(
                os.environ, {"ACTIVEWATCHER_WEB_DIST": str(custom)}, clear=False
            ):
                self.assertEqual(server_app._frontend_dist_dir(), custom)

        default = datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc)
        self.assertEqual(server_app._parse_dt_param(None, default=default), default)
        parsed = server_app._parse_dt_param("2026-03-01T12:00:00Z", default=default)
        self.assertEqual(parsed.isoformat(), "2026-03-01T12:00:00+00:00")
        with self.assertRaisesRegex(Exception, "invalid timestamp"):
            server_app._parse_dt_param("not-a-date", default=default)


class AppEndpointsTests(unittest.TestCase):
    def _create_client(
        self, *, with_frontend: bool
    ) -> tuple[TestClient, tempfile.TemporaryDirectory[str]]:
        tmp = tempfile.TemporaryDirectory()
        tmp_path = Path(tmp.name)
        db_path = tmp_path / "events.sqlite3"
        dist = tmp_path / "dist"
        dist.mkdir(parents=True, exist_ok=True)

        if with_frontend:
            (dist / "index.html").write_text(
                "<html><body>ok</body></html>", encoding="utf-8"
            )
            (dist / "favicon.svg").write_text("<svg></svg>", encoding="utf-8")
            assets_dir = dist / "assets"
            assets_dir.mkdir(parents=True, exist_ok=True)
            (assets_dir / "test.txt").write_text("asset-ok", encoding="utf-8")

        env = {
            "ACTIVEWATCHER_WEB_DIST": str(dist),
            "ACTIVEWATCHER_TRUSTED_HOSTS": "127.0.0.1,localhost",
            "ACTIVEWATCHER_CORS_ORIGINS": "http://127.0.0.1:5173,http://localhost:5173",
        }
        patcher = mock.patch.dict(os.environ, env, clear=False)
        patcher.start()
        self.addCleanup(patcher.stop)

        app = server_app.create_app(db_path)
        client = TestClient(app, base_url="http://127.0.0.1")
        client.__enter__()
        self.addCleanup(lambda: client.__exit__(None, None, None))
        self.addCleanup(tmp.cleanup)
        return client, tmp

    def test_ui_routes_without_frontend_build(self) -> None:
        client, _tmp = self._create_client(with_frontend=False)

        self.assertEqual(client.get("/health").status_code, 200)
        self.assertEqual(client.get("/meta").status_code, 200)
        root = client.get("/", follow_redirects=False)
        self.assertEqual(root.status_code, 302)
        self.assertEqual(root.headers.get("location"), "/ui")

        self.assertEqual(client.get("/ui").status_code, 503)
        self.assertEqual(client.get("/ui/").status_code, 503)
        self.assertEqual(client.get("/ui/stats").status_code, 503)
        self.assertEqual(client.get("/ui/timers").status_code, 503)
        self.assertEqual(client.get("/ui/settings").status_code, 503)
        self.assertEqual(client.get("/ui/any/route").status_code, 503)

        asset_path = client.get("/ui/assets/does-not-exist.js")
        self.assertEqual(asset_path.status_code, 404)
        self.assertEqual(asset_path.json()["detail"], "asset not found")

        missing_icon = client.get("/ui/favicon.svg")
        self.assertEqual(missing_icon.status_code, 404)

    def test_ui_routes_with_frontend_build_and_assets(self) -> None:
        client, _tmp = self._create_client(with_frontend=True)

        ui = client.get("/ui")
        self.assertEqual(ui.status_code, 200)
        self.assertIn("<html>", ui.text)

        spa = client.get("/ui/stats")
        self.assertEqual(spa.status_code, 200)
        self.assertIn("ok", spa.text)

        icon = client.get("/ui/favicon.svg")
        self.assertEqual(icon.status_code, 200)

        asset = client.get("/ui/assets/test.txt")
        self.assertEqual(asset.status_code, 200)
        self.assertEqual(asset.text, "asset-ok")

    def test_state_event_summary_apps_heatmap_categories(self) -> None:
        client, _tmp = self._create_client(with_frontend=False)

        first = client.post(
            "/v1/state",
            json=_state_payload(
                ts="2026-03-01T12:00:00Z",
                bucket="window",
                source="hyprland",
                data={"app": "Code", "title": "main.py"},
            ),
        )
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["status"], "ok")

        refresh = client.post(
            "/v1/state",
            json=_state_payload(
                ts="2026-03-01T12:00:30Z",
                bucket="window",
                source="hyprland",
                data={"app": "Code", "title": "main.py"},
            ),
        )
        self.assertEqual(refresh.status_code, 200)

        # Non-monotonic with changed payload maps to 409.
        conflict = client.post(
            "/v1/state",
            json=_state_payload(
                ts="2026-03-01T12:00:10Z",
                bucket="window",
                source="hyprland",
                data={"app": "Firefox", "title": "docs"},
            ),
        )
        self.assertEqual(conflict.status_code, 409)

        # Add idle and tabs for summary/categories/heatmap branches.
        self.assertEqual(
            client.post(
                "/v1/state",
                json=_state_payload(
                    ts="2026-03-01T12:00:00Z",
                    bucket="idle",
                    source="logind",
                    data={"afk": False},
                ),
            ).status_code,
            200,
        )
        self.assertEqual(
            client.post(
                "/v1/state",
                json=_state_payload(
                    ts="2026-03-01T12:01:00Z",
                    bucket="idle",
                    source="logind",
                    data={"afk": True},
                ),
            ).status_code,
            200,
        )
        self.assertEqual(
            client.post(
                "/v1/state",
                json=_state_payload(
                    ts="2026-03-01T12:01:30Z",
                    bucket="browser_tabs",
                    source="tabs:firefox",
                    data={
                        "browser": "Firefox",
                        "tabs": [{"url": "https://github.com", "title": "PR"}],
                    },
                ),
            ).status_code,
            200,
        )

        rng = client.get("/v1/range", params={"bucket": "window"})
        self.assertEqual(rng.status_code, 200)
        self.assertFalse(rng.json()["empty"])

        empty_range = client.get("/v1/range", params={"bucket": "workspace"})
        self.assertEqual(empty_range.status_code, 200)
        self.assertTrue(empty_range.json()["empty"])

        bad_events = client.get("/v1/events", params={"from": "bad"})
        self.assertEqual(bad_events.status_code, 422)

        events = client.get(
            "/v1/events",
            params={
                "bucket": "window",
                "from": "2026-03-01T12:00:00Z",
                "to": "2026-03-01T12:02:00Z",
            },
        )
        self.assertEqual(events.status_code, 200)
        self.assertGreaterEqual(len(events.json().get("events") or []), 1)

        summary = client.get(
            "/v1/summary",
            params={
                "from": "2026-03-01T12:00:00Z",
                "to": "2026-03-01T12:02:00Z",
                "chunk_seconds": 60,
                "include_timeline": "true",
            },
        )
        self.assertEqual(summary.status_code, 200)
        self.assertIn("top_apps", summary.json())

        apps = client.get(
            "/v1/apps",
            params={"from": "2026-03-01T12:00:00Z", "to": "2026-03-01T12:05:00Z"},
        )
        self.assertEqual(apps.status_code, 200)
        self.assertIn("Code", apps.json().get("apps") or [])

        heatmap_bad = client.get("/v1/heatmap", params={"mode": "bad"})
        self.assertEqual(heatmap_bad.status_code, 422)

        heatmap_ok = client.get(
            "/v1/heatmap",
            params={
                "from": "2026-03-01T12:00:00Z",
                "to": "2026-03-01T12:02:00Z",
                "mode": "auto",
                "tz": "UTC",
            },
        )
        self.assertEqual(heatmap_ok.status_code, 200)
        self.assertIn("days", heatmap_ok.json())

        categories_bad = client.get("/v1/categories", params={"mode": "bad"})
        self.assertEqual(categories_bad.status_code, 422)

        categories_ok = client.get(
            "/v1/categories",
            params={
                "from": "2026-03-01T12:00:00Z",
                "to": "2026-03-01T12:02:00Z",
                "mode": "auto",
            },
        )
        self.assertEqual(categories_ok.status_code, 200)
        self.assertIn("apps", categories_ok.json())

    def test_timer_endpoints(self) -> None:
        client, _tmp = self._create_client(with_frontend=False)

        invalid = client.post("/v1/timers", json={"name": "focus", "kind": "timer"})
        self.assertEqual(invalid.status_code, 422)

        created = client.post("/v1/timers", json={"name": "counter", "kind": "counter"})
        self.assertEqual(created.status_code, 200)
        timer_id = int(created.json()["timer"]["id"])

        self.assertEqual(client.get("/v1/timers").status_code, 200)
        self.assertEqual(client.post(f"/v1/timers/{timer_id}/start").status_code, 200)
        self.assertEqual(client.post(f"/v1/timers/{timer_id}/pause").status_code, 200)
        self.assertEqual(client.post(f"/v1/timers/{timer_id}/stop").status_code, 200)
        self.assertEqual(
            client.post(f"/v1/timers/{timer_id}/reactivate").status_code, 200
        )
        self.assertEqual(client.post(f"/v1/timers/{timer_id}/delete").status_code, 200)

        not_found = client.post(f"/v1/timers/{timer_id}/start")
        self.assertEqual(not_found.status_code, 404)

    def test_autotag_endpoint_error_mapping(self) -> None:
        client, _tmp = self._create_client(with_frontend=False)

        with mock.patch(
            "activewatcher.server.app.reports.list_autotag_runs",
            return_value={"runs": []},
        ):
            runs = client.get("/v1/autotag/runs", params={"limit": 10})
            self.assertEqual(runs.status_code, 200)
            self.assertEqual(runs.json(), {"runs": []})

        with mock.patch(
            "activewatcher.server.app.reports.autotag_decisions",
            side_effect=FileNotFoundError("missing"),
        ):
            resp = client.get("/v1/autotag/decisions")
            self.assertEqual(resp.status_code, 404)

        with mock.patch(
            "activewatcher.server.app.reports.autotag_decisions",
            side_effect=ValueError("bad run"),
        ):
            resp = client.get("/v1/autotag/decisions")
            self.assertEqual(resp.status_code, 422)

        with mock.patch(
            "activewatcher.server.app.reports.autotag_generated",
            side_effect=FileNotFoundError("missing"),
        ):
            resp = client.get("/v1/autotag/generated")
            self.assertEqual(resp.status_code, 404)

        with mock.patch(
            "activewatcher.server.app.reports.autotag_generated",
            side_effect=ValueError("bad run"),
        ):
            resp = client.get("/v1/autotag/generated")
            self.assertEqual(resp.status_code, 422)

        with mock.patch(
            "activewatcher.server.app.reports.approve_autotag_review_gate",
            return_value={"status": "ok"},
        ) as approve_mock:
            ok = client.post(
                "/v1/autotag/review-gate/approve",
                json={
                    "run_id": "run-1",
                    "approved_by": "tester",
                    "allowed_category_drop_ids": ["a", "b"],
                },
            )
            self.assertEqual(ok.status_code, 200)
            approve_mock.assert_called_once_with(
                run_id="run-1",
                approved_by="tester",
                allowed_category_drop_ids=["a", "b"],
            )

        with mock.patch(
            "activewatcher.server.app.reports.approve_autotag_review_gate",
            side_effect=ValueError("bad payload"),
        ):
            bad = client.post(
                "/v1/autotag/review-gate/approve",
                json={
                    "run_id": "run-1",
                    "approved_by": "tester",
                    "allowed_category_drop_ids": "not-a-list",
                },
            )
            self.assertEqual(bad.status_code, 422)


if __name__ == "__main__":
    unittest.main()
