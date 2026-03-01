from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from activewatcher_autotag.runtime import normalize_run_id, run_lock


class NormalizeRunIdTests(unittest.TestCase):
    def test_accepts_simple_run_id(self) -> None:
        self.assertEqual(
            normalize_run_id("run_20260228_abcd1234"), "run_20260228_abcd1234"
        )

    def test_rejects_path_like_run_ids(self) -> None:
        bad_values = ["../evil", "..", "/tmp/run", "run/child", "run\\child", ""]
        for value in bad_values:
            with self.assertRaises(ValueError):
                normalize_run_id(value)


class RunLockTests(unittest.TestCase):
    def test_stale_invalid_pid_lock_is_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            old_xdg_data_home = os.environ.get("XDG_DATA_HOME")
            os.environ["XDG_DATA_HOME"] = tmp
            try:
                lockfile = Path(tmp) / "activewatcher" / "autotag" / ".run.lock"
                lockfile.parent.mkdir(parents=True, exist_ok=True)
                lockfile.write_text(
                    json.dumps(
                        {
                            "pid": "not-a-number",
                            "host": "broken-host",
                            "started_at": "not-a-timestamp",
                            "run_id": "stale-run",
                        }
                    )
                    + "\n",
                    encoding="utf-8",
                )

                with run_lock(force_unlock=False):
                    self.assertTrue(lockfile.is_file())
            finally:
                if old_xdg_data_home is None:
                    os.environ.pop("XDG_DATA_HOME", None)
                else:
                    os.environ["XDG_DATA_HOME"] = old_xdg_data_home


if __name__ == "__main__":
    unittest.main()
