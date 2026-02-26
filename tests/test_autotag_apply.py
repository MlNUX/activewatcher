from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from activewatcher_autotag.apply import _require_review_gate, run_apply
from activewatcher_autotag.runtime import file_sha256, read_json, write_json


def _write_generated(run_root: Path) -> tuple[dict[str, object], str]:
    payload: dict[str, object] = {
        "categories": [
            {"id": "coding", "label": "Coding"},
            {"id": "other", "label": "Other"},
        ]
    }
    path = run_root / "categories.generated.json"
    write_json(path, payload)
    return payload, file_sha256(path)


class ApplyReviewGateTests(unittest.TestCase):
    def test_require_review_gate_bootstraps_from_template(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp) / "run_bootstrap"
            run_root.mkdir(parents=True, exist_ok=True)
            _, generated_sha = _write_generated(run_root)

            write_json(
                run_root / "review-gate.template.json",
                {
                    "run_id": run_root.name,
                    "approved": True,
                    "approved_by": "tester",
                    "approved_at": "2026-02-26T14:30:00Z",
                    "categories_generated_sha256": generated_sha,
                    "allowed_category_drop_ids": [],
                },
            )

            payload = _require_review_gate(run_root, generated_sha)

            self.assertTrue((run_root / "review-gate.json").is_file())
            self.assertTrue(bool(payload.get("approved")))

    def test_require_review_gate_fails_when_no_gate_files_exist(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp) / "run_missing"
            run_root.mkdir(parents=True, exist_ok=True)
            with self.assertRaisesRegex(
                ValueError, "missing review gate file: review-gate.json"
            ):
                _require_review_gate(run_root, "deadbeef")


class ApplyFlowTests(unittest.TestCase):
    def test_run_apply_accepts_template_only_gate_for_existing_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "run_apply"
            run_root.mkdir(parents=True, exist_ok=True)
            expected_payload, generated_sha = _write_generated(run_root)

            write_json(
                run_root / "review-gate.template.json",
                {
                    "run_id": run_root.name,
                    "approved": True,
                    "approved_by": "tester",
                    "approved_at": "2026-02-26T14:30:00Z",
                    "categories_generated_sha256": generated_sha,
                    "allowed_category_drop_ids": [],
                },
            )
            write_json(
                run_root / "evaluation.json",
                {
                    "run_id": run_root.name,
                    "categories_generated_sha256": generated_sha,
                    "gates": {"recommend_apply": True},
                },
            )

            target = root / "categories.json"
            result = run_apply(run_root=run_root, categories_path=target)

            self.assertTrue(target.is_file())
            self.assertTrue((run_root / "review-gate.json").is_file())
            self.assertEqual(result.get("backup"), None)
            self.assertEqual(read_json(target), expected_payload)


if __name__ == "__main__":
    unittest.main()
