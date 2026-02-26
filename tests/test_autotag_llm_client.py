from __future__ import annotations

import unittest

from activewatcher_autotag.llm_client import LlmError, validate_local_base_url


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

    def test_rejects_relative_unix_path(self) -> None:
        with self.assertRaises(LlmError):
            validate_local_base_url("unix://relative.sock")


if __name__ == "__main__":
    unittest.main()
