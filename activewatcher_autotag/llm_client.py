from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse


class LlmError(RuntimeError):
    pass


class LlmContextOverflowError(LlmError):
    pass


def _is_local_host(host: str) -> bool:
    h = str(host or "").strip().lower().strip("[]")
    return h in {"localhost", "127.0.0.1", "::1"}


def _normalize_unix_socket_url(raw: str) -> str:
    if raw.startswith("unix://"):
        path = raw[len("unix://") :]
        if not path.startswith("/"):
            raise LlmError("unix socket path must be absolute")
        return f"unix://{path}"

    parsed = urlparse(raw)
    if parsed.scheme != "http+unix":
        raise LlmError("unsupported unix socket URL scheme")

    encoded = ""
    if parsed.netloc:
        encoded += parsed.netloc
    if parsed.path:
        encoded += parsed.path
    socket_path = unquote(encoded)
    if not socket_path.startswith("/"):
        raise LlmError("unix socket path must be absolute")
    return f"unix://{socket_path}"


def validate_local_base_url(base_url: str) -> str:
    raw = str(base_url or "").strip()
    if not raw:
        raise LlmError("empty LLM base URL")
    if raw.startswith("unix://") or raw.startswith("http+unix://"):
        return _normalize_unix_socket_url(raw)
    parsed = urlparse(raw)
    if parsed.scheme not in {"http", "https"}:
        raise LlmError("LLM base URL must use http or https")
    if not _is_local_host(parsed.hostname or ""):
        raise LlmError("LLM base URL must be local-only (localhost/127.0.0.1/::1)")
    path = parsed.path.rstrip("/")
    suffix = path if path else ""
    return f"{parsed.scheme}://{parsed.netloc}{suffix}"


def render_template(template_text: str, values: dict[str, str]) -> str:
    out = template_text
    for key, value in values.items():
        out = out.replace(f"{{{{{key}}}}}", str(value))
    return out


def read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


@dataclass(frozen=True)
class LlmRequest:
    model: str
    system_prompt: str
    user_prompt: str
    temperature: float
    top_p: float
    timeout_seconds: int
    max_retries: int


class OllamaClient:
    def __init__(self, *, base_url: str) -> None:
        self.base_url = validate_local_base_url(base_url)
        self._uds_path = ""
        if self.base_url.startswith("unix://"):
            self._uds_path = self.base_url[len("unix://") :]
        try:
            import httpx  # type: ignore
        except ImportError as e:
            raise LlmError("Missing dependency: httpx") from e
        self._httpx = httpx

    def _raise_http_error(self, resp: Any) -> None:
        text = str(resp.text or "")
        status = int(resp.status_code)
        lowered = text.lower()
        if (
            "context" in lowered
            or "too long" in lowered
            or "token" in lowered
            and "limit" in lowered
        ):
            raise LlmContextOverflowError(
                f"LLM context overflow ({status}): {text[:200]}"
            )
        raise LlmError(f"LLM request failed ({status}): {text[:200]}")

    def complete_json(self, request: LlmRequest) -> str:
        payload = {
            "model": request.model,
            "stream": False,
            "system": request.system_prompt,
            "prompt": request.user_prompt,
            "format": "json",
            "options": {
                "temperature": float(request.temperature),
                "top_p": float(request.top_p),
            },
        }
        url = (
            "http://localhost/api/generate"
            if self._uds_path
            else f"{self.base_url}/api/generate"
        )
        attempts = max(0, int(request.max_retries)) + 1

        last_error: Exception | None = None
        for _ in range(attempts):
            try:
                client_kwargs: dict[str, Any] = {
                    "timeout": float(request.timeout_seconds)
                }
                if self._uds_path:
                    client_kwargs["transport"] = self._httpx.HTTPTransport(
                        uds=self._uds_path
                    )
                with self._httpx.Client(**client_kwargs) as client:
                    resp = client.post(url, json=payload)
                if resp.status_code >= 400:
                    self._raise_http_error(resp)
                body = resp.json()
                if not isinstance(body, dict):
                    raise LlmError("LLM response is not JSON object")
                response_text = str(body.get("response") or "").strip()
                if not response_text:
                    raise LlmError("LLM response text is empty")
                return response_text
            except LlmContextOverflowError:
                raise
            except Exception as e:
                last_error = e
                continue
        raise LlmError(f"LLM request failed after retries: {last_error}")


def safe_json_dump(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
