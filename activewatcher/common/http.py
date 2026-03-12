from __future__ import annotations

import os
from typing import Any


class ActiveWatcherClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 10.0,
        write_token: str | None = None,
    ) -> None:
        try:
            import httpx  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "Missing dependency: httpx. Install it (e.g. `pip install httpx`) to use client commands."
            ) from e

        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout_seconds)
        resolved_write_token = str(
            write_token
            if write_token is not None
            else os.environ.get("ACTIVEWATCHER_WRITE_TOKEN", "")
        ).strip()
        self._auth_headers = (
            {"X-ActiveWatcher-Token": resolved_write_token}
            if resolved_write_token
            else None
        )

    def close(self) -> None:
        self._client.close()

    def get_json(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        resp = self._client.get(
            f"{self._base_url}{path}",
            params=params,
            headers=self._auth_headers,
        )
        resp.raise_for_status()
        return resp.json()


class ActiveWatcherAsyncClient:
    def __init__(
        self,
        base_url: str,
        *,
        timeout_seconds: float = 5.0,
        write_token: str | None = None,
    ) -> None:
        try:
            import httpx  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "Missing dependency: httpx. Install it (e.g. `pip install httpx`) to run watchers."
            ) from e

        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout_seconds)
        resolved_write_token = str(
            write_token
            if write_token is not None
            else os.environ.get("ACTIVEWATCHER_WRITE_TOKEN", "")
        ).strip()
        self._auth_headers = (
            {"X-ActiveWatcher-Token": resolved_write_token}
            if resolved_write_token
            else None
        )

    async def aclose(self) -> None:
        await self._client.aclose()

    async def post_state(self, payload: dict[str, Any]) -> dict[str, Any]:
        resp = await self._client.post(
            f"{self._base_url}/v1/state",
            json=payload,
            headers=self._auth_headers,
        )
        resp.raise_for_status()
        return resp.json()
