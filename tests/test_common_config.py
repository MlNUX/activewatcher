from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from activewatcher.common import config


class CommonConfigTests(unittest.TestCase):
    def tearDown(self) -> None:
        config._load_runtime_config.cache_clear()

    def test_default_paths_follow_xdg_env(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            data_home = Path(tmp) / "data"
            config_home = Path(tmp) / "cfg"
            with unittest.mock.patch.dict(
                os.environ,
                {
                    "XDG_DATA_HOME": str(data_home),
                    "XDG_CONFIG_HOME": str(config_home),
                },
                clear=False,
            ):
                self.assertEqual(config.xdg_data_home(), data_home)
                self.assertEqual(config.default_data_dir(), data_home / "activewatcher")
                self.assertEqual(config.xdg_config_home(), config_home)
                self.assertEqual(
                    config.default_config_path(),
                    config_home / "activewatcher" / "config.toml",
                )

    def test_default_path_env_overrides(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            custom_cfg = Path(tmp) / "custom.toml"
            custom_db = Path(tmp) / "db.sqlite3"
            custom_categories = Path(tmp) / "cats.json"
            with unittest.mock.patch.dict(
                os.environ,
                {
                    "ACTIVEWATCHER_CONFIG_PATH": str(custom_cfg),
                    "ACTIVEWATCHER_DB_PATH": str(custom_db),
                    "ACTIVEWATCHER_CATEGORIES_PATH": str(custom_categories),
                },
                clear=False,
            ):
                self.assertEqual(config.default_config_path(), custom_cfg)
                self.assertEqual(config.default_db_path(), custom_db)
                self.assertEqual(config.default_categories_path(), custom_categories)

    def test_runtime_config_and_env_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "config.toml"
            cfg_path.write_text(
                "\n".join(
                    [
                        "[watch]",
                        'server_url = "http://cfg.local:8712"',
                        "",
                        "[watch.hyprland]",
                        "track_focused = false",
                        "debounce_ms = 333",
                        "",
                        "[dashboard]",
                        "refresh_seconds = 2.5",
                        "",
                        "[server]",
                        "stale_after_seconds = 77",
                        'cors_origins = ["http://cfg:5173", "http://cfg:5173", ""]',
                    ]
                ),
                encoding="utf-8",
            )

            with unittest.mock.patch.dict(
                os.environ,
                {
                    "ACTIVEWATCHER_CONFIG_PATH": str(cfg_path),
                    "ACTIVEWATCHER_TRACK_FOCUSED": "1",
                    "ACTIVEWATCHER_HYPRLAND_DEBOUNCE_MS": "120",
                    "ACTIVEWATCHER_DASHBOARD_REFRESH_SECONDS": "4.5",
                    "ACTIVEWATCHER_SERVER_URL": "http://env.local:8712",
                    "ACTIVEWATCHER_STALE_AFTER_SECONDS": "15",
                    "ACTIVEWATCHER_CORS_ORIGINS": "http://env:5173,http://env2:5173",
                },
                clear=False,
            ):
                config._load_runtime_config.cache_clear()

                self.assertTrue(
                    config.config_bool(
                        ("watch", "hyprland", "track_focused"),
                        env_var="ACTIVEWATCHER_TRACK_FOCUSED",
                        default=False,
                    )
                )
                self.assertEqual(
                    config.config_int(
                        ("watch", "hyprland", "debounce_ms"),
                        env_var="ACTIVEWATCHER_HYPRLAND_DEBOUNCE_MS",
                        default=999,
                    ),
                    120,
                )
                self.assertEqual(
                    config.config_float(
                        ("dashboard", "refresh_seconds"),
                        env_var="ACTIVEWATCHER_DASHBOARD_REFRESH_SECONDS",
                        default=1.0,
                    ),
                    4.5,
                )
                self.assertEqual(config.default_server_url(), "http://env.local:8712")
                self.assertEqual(config.default_stale_after_seconds(), 15)
                self.assertEqual(
                    config.config_str_list(
                        ("server", "cors_origins"),
                        env_var="ACTIVEWATCHER_CORS_ORIGINS",
                        default=["http://fallback:5173"],
                    ),
                    ["http://env:5173", "http://env2:5173"],
                )

            # Without env override, values come from config file.
            with unittest.mock.patch.dict(
                os.environ,
                {"ACTIVEWATCHER_CONFIG_PATH": str(cfg_path)},
                clear=True,
            ):
                config._load_runtime_config.cache_clear()
                self.assertFalse(
                    config.config_bool(
                        ("watch", "hyprland", "track_focused"), default=True
                    )
                )
                self.assertEqual(
                    config.config_int(("watch", "hyprland", "debounce_ms"), default=1),
                    333,
                )
                self.assertAlmostEqual(
                    config.config_float(("dashboard", "refresh_seconds"), default=0.1),
                    2.5,
                )
                self.assertEqual(config.default_stale_after_seconds(), 77)

    def test_parse_helpers_cover_edge_cases(self) -> None:
        self.assertIs(config._parse_bool(True), True)
        self.assertIs(config._parse_bool(0), False)
        self.assertIs(config._parse_bool("YES"), True)
        self.assertIs(config._parse_bool("off"), False)
        self.assertIsNone(config._parse_bool("maybe"))

        self.assertEqual(config._parse_int(5), 5)
        self.assertEqual(config._parse_int(7.0), 7)
        self.assertEqual(config._parse_int("42"), 42)
        self.assertIsNone(config._parse_int(True))
        self.assertIsNone(config._parse_int(""))
        self.assertIsNone(config._parse_int("x"))

        self.assertEqual(config._parse_float(1), 1.0)
        self.assertEqual(config._parse_float("3.5"), 3.5)
        self.assertIsNone(config._parse_float(False))
        self.assertIsNone(config._parse_float("nope"))

        self.assertEqual(config._parse_str(" hello "), "hello")
        self.assertIsNone(config._parse_str(" "))
        self.assertEqual(config._parse_str(" ", allow_empty=True), "")

        self.assertEqual(
            config._parse_str_list("a,b,a,, c"),
            ["a", "b", "c"],
        )
        self.assertEqual(config._parse_str_list(["x", "x", " ", "y"]), ["x", "y"])
        self.assertEqual(config._parse_str_list([], allow_empty=True), [])
        self.assertIsNone(config._parse_str_list(123))

    def test_load_runtime_config_invalid_toml_returns_empty(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            cfg_path = Path(tmp) / "config.toml"
            cfg_path.write_text("[broken", encoding="utf-8")
            with unittest.mock.patch.dict(
                os.environ,
                {"ACTIVEWATCHER_CONFIG_PATH": str(cfg_path)},
                clear=False,
            ):
                config._load_runtime_config.cache_clear()
                self.assertEqual(config._load_runtime_config(), {})

    def test_ensure_parent_dir_creates_parent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "a" / "b" / "file.sqlite3"
            self.assertFalse(target.parent.exists())
            config.ensure_parent_dir(target)
            self.assertTrue(target.parent.exists())


if __name__ == "__main__":
    unittest.main()
