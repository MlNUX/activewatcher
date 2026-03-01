from __future__ import annotations

import unittest

from activewatcher_autotag.llm_client import (
    LlmContextOverflowError,
    LlmError,
    OllamaClient,
    validate_local_base_url,
)


class ValidateLocalBaseUrlTests(unittest.TestCase):
    def test_accepts_local_http_url(self) -> None:
        self.assertEqual(
            validate_local_base_url("http://127.0.0.1:11434"),
            "http://127.0.0.1:11434",
        )

    def test_rejects_remote_host(self) -> None:
        with self.assertRaises(LlmError):
            validate_local_base_url("https://example.com")

    def test_accepts_unix_scheme(self) -> None:
        self.assertEqual(
            validate_local_base_url("unix:///var/run/ollama.sock"),
            "unix:///var/run/ollama.sock",
        )

    def test_accepts_http_unix_encoded(self) -> None:
        self.assertEqual(
            validate_local_base_url("http+unix://%2Fvar%2Frun%2Follama.sock"),
            "unix:///var/run/ollama.sock",
        )

    def test_accepts_http_unix_encoded_with_api_path(self) -> None:
        self.assertEqual(
            validate_local_base_url("http+unix://%2Fvar%2Frun%2Follama.sock/api"),
            "unix:///var/run/ollama.sock",
        )

    def test_accepts_http_unix_partially_encoded_socket_path(self) -> None:
        self.assertEqual(
            validate_local_base_url("http+unix://%2Fvar%2Frun/ollama.sock"),
            "unix:///var/run/ollama.sock",
        )

    def test_rejects_relative_unix_path(self) -> None:
        with self.assertRaises(LlmError):
            validate_local_base_url("unix://relative.sock")


class _FakeResponse:
    def __init__(self, status_code: int, text: str) -> None:
        self.status_code = status_code
        self.text = text


class RaiseHttpErrorTests(unittest.TestCase):
    """Tests for OllamaClient._raise_http_error context overflow detection."""

    def _make_client(self) -> OllamaClient:
        return OllamaClient(base_url="http://127.0.0.1:11434")

    def test_context_keyword_triggers_overflow(self) -> None:
        client = self._make_client()
        with self.assertRaises(LlmContextOverflowError):
            client._raise_http_error(_FakeResponse(400, "context length exceeded"))

    def test_too_long_keyword_triggers_overflow(self) -> None:
        client = self._make_client()
        with self.assertRaises(LlmContextOverflowError):
            client._raise_http_error(_FakeResponse(400, "input is too long"))

    def test_token_and_limit_together_triggers_overflow(self) -> None:
        client = self._make_client()
        with self.assertRaises(LlmContextOverflowError):
            client._raise_http_error(_FakeResponse(400, "token limit exceeded"))

    def test_token_alone_does_not_trigger_overflow(self) -> None:
        client = self._make_client()
        with self.assertRaises(LlmError) as ctx:
            client._raise_http_error(_FakeResponse(400, "invalid token format"))
        self.assertNotIsInstance(ctx.exception, LlmContextOverflowError)

    def test_generic_error_raises_llm_error(self) -> None:
        client = self._make_client()
        with self.assertRaises(LlmError) as ctx:
            client._raise_http_error(_FakeResponse(500, "internal server error"))
        self.assertNotIsInstance(ctx.exception, LlmContextOverflowError)


if __name__ == "__main__":
    unittest.main()
