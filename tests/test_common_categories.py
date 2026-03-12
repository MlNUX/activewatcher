from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from activewatcher.common import categories


class CommonCategoriesTests(unittest.TestCase):
    def tearDown(self) -> None:
        categories.clear_category_catalog_cache()

    def test_category_catalog_reloads_when_override_file_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            categories_path = Path(tmp) / "categories.json"
            categories_path.write_text(
                json.dumps(
                    {
                        "categories": [
                            {
                                "id": "focus",
                                "label": "Focus",
                                "color": "#00ffaa",
                                "apps": ["myeditor"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            with mock.patch.dict(
                os.environ,
                {"ACTIVEWATCHER_CATEGORIES_PATH": str(categories_path)},
                clear=False,
            ):
                categories.clear_category_catalog_cache()
                first = categories.category_catalog()
                self.assertEqual(first.source, f"file:{categories_path}")
                self.assertEqual(first.classify_app(app="myeditor"), "focus")

                categories_path.write_text(
                    json.dumps(
                        {
                            "categories": [
                                {
                                    "id": "chat",
                                    "label": "Chat",
                                    "color": "#33aaff",
                                    "apps": ["chatclient"],
                                }
                            ]
                        }
                    ),
                    encoding="utf-8",
                )

                second = categories.category_catalog()
                self.assertEqual(second.source, f"file:{categories_path}")
                self.assertEqual(second.classify_app(app="chatclient"), "chat")
                self.assertNotEqual(first.rules[0].id, second.rules[0].id)


if __name__ == "__main__":
    unittest.main()
