from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from activewatcher_autotag.apply import _require_review_gate, run_apply
from activewatcher_autotag.runtime import file_sha256, read_json, write_json


def _ok_gates() -> dict[str, bool]:
    return {
        "hard_policy_ok": True,
        "schema_valid_outputs": True,
        "other_not_worse": True,
        "category_drop_guard": True,
        "goldset_exists": True,
        "goldset_size_ok": True,
        "goldset_f1_not_lower": True,
        "pass_b_apply_ok": True,
    }


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

    def test_require_review_gate_rejects_non_boolean_approved(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            run_root = Path(tmp) / "run_bad_approved"
            run_root.mkdir(parents=True, exist_ok=True)
            _, generated_sha = _write_generated(run_root)

            write_json(
                run_root / "review-gate.template.json",
                {
                    "run_id": run_root.name,
                    "approved": "true",
                    "approved_by": "tester",
                    "approved_at": "2026-02-26T14:30:00Z",
                    "categories_generated_sha256": generated_sha,
                    "allowed_category_drop_ids": [],
                },
            )

            with self.assertRaisesRegex(ValueError, "review gate not approved"):
                _require_review_gate(run_root, generated_sha)

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
                    "gates": _ok_gates(),
                },
            )

            target = root / "categories.json"
            result = run_apply(run_root=run_root, categories_path=target)

            self.assertTrue(target.is_file())
            self.assertTrue((run_root / "review-gate.json").is_file())
            self.assertEqual(result.get("backup"), None)
            self.assertEqual(read_json(target), expected_payload)

    def test_run_apply_accepts_legacy_recommend_apply_true(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "run_legacy_eval_true"
            run_root.mkdir(parents=True, exist_ok=True)
            expected_payload, generated_sha = _write_generated(run_root)

            write_json(
                run_root / "review-gate.json",
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
            run_apply(run_root=run_root, categories_path=target)
            self.assertEqual(read_json(target), expected_payload)

    def test_run_apply_rejects_legacy_recommend_apply_false(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "run_legacy_eval_false"
            run_root.mkdir(parents=True, exist_ok=True)
            _, generated_sha = _write_generated(run_root)

            write_json(
                run_root / "review-gate.json",
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
                    "gates": {"recommend_apply": False},
                },
            )

            with self.assertRaisesRegex(ValueError, "apply is blocked"):
                run_apply(run_root=run_root, categories_path=root / "categories.json")

    def test_run_apply_rejects_non_boolean_or_missing_eval_gates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run_root = root / "run_bad_eval"
            run_root.mkdir(parents=True, exist_ok=True)
            _, generated_sha = _write_generated(run_root)

            write_json(
                run_root / "review-gate.json",
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
                    "gates": {
                        **_ok_gates(),
                        "hard_policy_ok": "true",
                    },
                },
            )

            with self.assertRaisesRegex(ValueError, "not boolean"):
                run_apply(run_root=run_root, categories_path=root / "categories.json")


if __name__ == "__main__":
    unittest.main()
