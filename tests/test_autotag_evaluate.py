from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from activewatcher_autotag.evaluate import (
    _build_catalog,
    _classify_app,
    _classify_tab,
    _flat_taxonomy_ok,
    _llm_local_only_ok,
    _max_new_categories_ok,
    _new_category_combined_floor_ok,
)
from activewatcher_autotag.settings import THRESHOLDS


class EvaluateClassifierTests(unittest.TestCase):
    def test_classify_app_uses_title_regex(self) -> None:
        catalog = _build_catalog(
            [
                {
                    "id": "research",
                    "apps": [],
                    "domains": [],
                    "titles": [],
                    "urls": [],
                    "title_regex": [r"\brfc\s+\d{3,5}\b"],
                },
                {"id": "other"},
            ]
        )
        predicted = _classify_app(catalog, app="firefox", title="Reading RFC 9110")
        self.assertEqual(predicted, "research")

    def test_classify_tab_uses_title_regex(self) -> None:
        catalog = _build_catalog(
            [
                {
                    "id": "learning",
                    "apps": [],
                    "domains": [],
                    "titles": [],
                    "urls": [],
                    "title_regex": [r"^python\s+tutorial"],
                },
                {"id": "other"},
            ]
        )
        predicted = _classify_tab(
            catalog,
            url="https://example.org/guide",
            title="Python Tutorial - Intro",
            app="chrome",
        )
        self.assertEqual(predicted, "learning")


class EvaluateHardPolicyTests(unittest.TestCase):
    def test_flat_taxonomy_guard_detects_parent_links(self) -> None:
        self.assertFalse(
            _flat_taxonomy_ok(
                [
                    {"id": "coding", "parent_id": "work"},
                    {"id": "other"},
                ]
            )
        )

    def test_llm_local_only_guard_accepts_unix_socket(self) -> None:
        metadata = {
            "llm": {
                "provider": "ollama",
                "base_url": "unix:///var/run/ollama.sock",
            }
        }
        self.assertTrue(_llm_local_only_ok(metadata))

    def test_llm_local_only_guard_rejects_remote(self) -> None:
        metadata = {
            "llm": {
                "provider": "ollama",
                "base_url": "https://example.com",
            }
        }
        self.assertFalse(_llm_local_only_ok(metadata))

    def test_new_category_combined_floor_guard(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp)
            rows = [
                {
                    "decision_type": "pass_b_member",
                    "target_category_id": "newcat",
                    "entity_type": "app",
                    "entity": f"app-{i}",
                }
                for i in range(6)
            ] + [
                {
                    "decision_type": "pass_b_member",
                    "target_category_id": "newcat",
                    "entity_type": "domain",
                    "entity": f"example{i}.com",
                }
                for i in range(4)
            ]
            (run_root / "autotag-decisions.jsonl").write_text(
                "\n".join(json.dumps(row) for row in rows) + "\n",
                encoding="utf-8",
            )
            self.assertTrue(_new_category_combined_floor_ok(run_root))

    def test_new_category_combined_floor_guard_rejects_small_group(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp)
            rows = [
                {
                    "decision_type": "pass_b_member",
                    "target_category_id": "tiny",
                    "entity_type": "app",
                    "entity": f"app-{i}",
                }
                for i in range(THRESHOLDS.new_category_min_combined_entities - 1)
            ]
            (run_root / "autotag-decisions.jsonl").write_text(
                "\n".join(json.dumps(row) for row in rows) + "\n",
                encoding="utf-8",
            )
            self.assertFalse(_new_category_combined_floor_ok(run_root))

    def test_max_new_categories_guard(self) -> None:
        self.assertTrue(_max_new_categories_ok({"accepted_proposals": 1}))
        self.assertFalse(
            _max_new_categories_ok(
                {"accepted_proposals": THRESHOLDS.max_new_categories + 1}
            )
        )


if __name__ == "__main__":
    unittest.main()
