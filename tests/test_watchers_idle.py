from __future__ import annotations

import os
import unittest
from datetime import datetime, timezone
from unittest import mock

from activewatcher.watchers import idle


class IdleWatcherLogicTests(unittest.TestCase):
    def test_compute_afk_defaults_to_not_afk_when_idle_hints_missing(self) -> None:
        decision = idle._compute_afk(
            props={},
            threshold_seconds=120,
            force_afk=False,
            now_utc=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
        )
        self.assertFalse(decision.afk)
        self.assertIsNone(decision.transition_ts)

    def test_compute_afk_force_overrides_missing_hints(self) -> None:
        decision = idle._compute_afk(
            props={},
            threshold_seconds=120,
            force_afk=True,
            now_utc=datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc),
        )
        self.assertTrue(decision.afk)
        self.assertIsNotNone(decision.transition_ts)


class IdleSessionSelectionTests(unittest.IsolatedAsyncioTestCase):
    async def test_get_session_id_prefers_active_session(self) -> None:
        async def fake_run(cmd: list[str]) -> str:
            if cmd[:2] == ["loginctl", "list-sessions"]:
                return "10 1000 leo seat0\n11 1000 leo seat0\n"

            if cmd[:3] == ["loginctl", "show-session", "10"] and "LockedHint" in cmd:
                return "LockedHint=no\nIdleHint=no\nIdleSinceHint=0\nIdleSinceHintMonotonic=0\n"
            if cmd[:3] == ["loginctl", "show-session", "11"] and "LockedHint" in cmd:
                return "LockedHint=no\nIdleHint=no\nIdleSinceHint=0\nIdleSinceHintMonotonic=0\n"

            if cmd[:3] == ["loginctl", "show-session", "10"] and "Active" in cmd:
                return "Active=no\nState=closing\n"
            if cmd[:3] == ["loginctl", "show-session", "11"] and "Active" in cmd:
                return "Active=yes\nState=active\n"

            raise AssertionError(f"Unexpected command: {cmd}")

        with (
            mock.patch.dict(os.environ, {}, clear=True),
            mock.patch("activewatcher.watchers.idle.os.getuid", return_value=1000),
            mock.patch("activewatcher.watchers.idle._run", side_effect=fake_run),
        ):
            session_id = await idle._get_session_id()
        self.assertEqual(session_id, "11")

    async def test_get_session_id_uses_env_override_when_available(self) -> None:
        with (
            mock.patch.dict(os.environ, {"XDG_SESSION_ID": "env-session"}, clear=True),
            mock.patch("activewatcher.watchers.idle._run") as run_mock,
        ):
            session_id = await idle._get_session_id()
        self.assertEqual(session_id, "env-session")
        run_mock.assert_not_called()


if __name__ == "__main__":
    unittest.main()
