from __future__ import annotations

import unittest
from typing import Any
from unittest import mock

from activewatcher.watchers import hyprland


class _FakeAsyncClient:
    def __init__(self, *, fail_on_bucket: str | None = None) -> None:
        self.fail_on_bucket = fail_on_bucket
        self.payloads: list[dict[str, Any]] = []
        self.closed = False

    async def post_state(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.payloads.append(payload)
        if self.fail_on_bucket and payload.get("bucket") == self.fail_on_bucket:
            raise RuntimeError("post failed")
        return {"status": "ok"}

    async def aclose(self) -> None:
        self.closed = True


def _watcher() -> hyprland.HyprlandWatcher:
    return hyprland.HyprlandWatcher(
        server_url="http://127.0.0.1:8712",
        source="hyprland",
        debounce_ms=100,
        title_max_len=120,
        heartbeat_seconds=30,
        track_focused=True,
        track_visible_windows=True,
        visible_all_monitors=False,
        track_open_apps=True,
        track_workspaces=True,
    )


class HyprlandWatcherPostingTests(unittest.IsolatedAsyncioTestCase):
    async def test_post_payloads_posts_all_and_closes_client(self) -> None:
        fake_client = _FakeAsyncClient()
        watcher = _watcher()

        with mock.patch(
            "activewatcher.watchers.hyprland.ActiveWatcherAsyncClient",
            return_value=fake_client,
        ):
            ok = await watcher._post_payloads(
                [
                    {"bucket": "window", "source": "s1", "data": {}},
                    {"bucket": "workspace", "source": "s2", "data": {}},
                ]
            )

        self.assertTrue(ok)
        self.assertEqual(len(fake_client.payloads), 2)
        self.assertTrue(fake_client.closed)

    async def test_post_payloads_returns_false_on_send_error(self) -> None:
        fake_client = _FakeAsyncClient(fail_on_bucket="workspace")
        watcher = _watcher()

        with mock.patch(
            "activewatcher.watchers.hyprland.ActiveWatcherAsyncClient",
            return_value=fake_client,
        ):
            ok = await watcher._post_payloads(
                [
                    {"bucket": "window", "source": "s1", "data": {}},
                    {"bucket": "workspace", "source": "s2", "data": {}},
                ]
            )

        self.assertFalse(ok)
        self.assertTrue(fake_client.closed)


if __name__ == "__main__":
    unittest.main()
