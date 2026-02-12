from __future__ import annotations

from typing import Any


class ActiveWatcherClient:
    def __init__(self, base_url: str, *, timeout_seconds: float = 10.0) -> None:
        try:
            import httpx  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "Missing dependency: httpx. Install it (e.g. `pip install httpx`) to use client commands."
            ) from e

        self._base_url = base_url.rstrip("/")
        self._client = httpx.Client(timeout=timeout_seconds)

    def close(self) -> None:
        self._client.close()

    def get_json(self, path: str, *, params: dict[str, Any] | None = None) -> Any:
        resp = self._client.get(f"{self._base_url}{path}", params=params)
        resp.raise_for_status()
        return resp.json()


class ActiveWatcherAsyncClient:
    def __init__(self, base_url: str, *, timeout_seconds: float = 5.0) -> None:
        try:
            import httpx  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise RuntimeError(
                "Missing dependency: httpx. Install it (e.g. `pip install httpx`) to run watchers."
            ) from e

        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout_seconds)

    async def aclose(self) -> None:
        await self._client.aclose()

    async def post_state(self, payload: dict[str, Any]) -> dict[str, Any]:
        resp = await self._client.post(f"{self._base_url}/v1/state", json=payload)
        resp.raise_for_status()
        return resp.json()
