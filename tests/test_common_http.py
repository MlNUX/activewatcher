from __future__ import annotations

import builtins
import unittest
from unittest import mock

from activewatcher.common.http import ActiveWatcherAsyncClient, ActiveWatcherClient


class _FakeResponse:
    def __init__(self, payload: dict):
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self):
        return self._payload


class CommonHttpTests(unittest.IsolatedAsyncioTestCase):
    def test_client_get_json_and_close(self) -> None:
        fake_httpx_client = mock.Mock()
        fake_httpx_client.get.return_value = _FakeResponse({"ok": True})

        with mock.patch("httpx.Client", return_value=fake_httpx_client):
            client = ActiveWatcherClient("http://127.0.0.1:8712")
            value = client.get_json("/v1/test", params={"a": "b"})
            self.assertEqual(value, {"ok": True})
            fake_httpx_client.get.assert_called_once_with(
                "http://127.0.0.1:8712/v1/test", params={"a": "b"}
            )
            client.close()
            fake_httpx_client.close.assert_called_once()

    async def test_async_client_post_state_and_close(self) -> None:
        fake_async_client = mock.AsyncMock()
        fake_async_client.post.return_value = _FakeResponse({"status": "ok"})

        with mock.patch("httpx.AsyncClient", return_value=fake_async_client):
            client = ActiveWatcherAsyncClient("http://127.0.0.1:8712")
            payload = {
                "bucket": "window",
                "source": "src",
                "ts": "2026-01-01T00:00:00Z",
                "data": {},
            }
            value = await client.post_state(payload)
            self.assertEqual(value, {"status": "ok"})
            fake_async_client.post.assert_awaited_once_with(
                "http://127.0.0.1:8712/v1/state", json=payload
            )
            await client.aclose()
            fake_async_client.aclose.assert_awaited_once()

    def test_missing_httpx_dependency_raises_runtime_error(self) -> None:
        real_import = builtins.__import__

        def _fake_import(name, *args, **kwargs):
            if name == "httpx":
                raise ImportError("missing")
            return real_import(name, *args, **kwargs)

        with mock.patch("builtins.__import__", side_effect=_fake_import):
            with self.assertRaisesRegex(RuntimeError, "Missing dependency: httpx"):
                ActiveWatcherClient("http://127.0.0.1:8712")
            with self.assertRaisesRegex(RuntimeError, "Missing dependency: httpx"):
                ActiveWatcherAsyncClient("http://127.0.0.1:8712")


if __name__ == "__main__":
    unittest.main()
