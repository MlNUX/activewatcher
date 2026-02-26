from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from activewatcher.server import reports


class AutotagReportsTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self._old_xdg_data_home = os.environ.get("XDG_DATA_HOME")
        os.environ["XDG_DATA_HOME"] = self._tmp.name

    def tearDown(self) -> None:
        if self._old_xdg_data_home is None:
            os.environ.pop("XDG_DATA_HOME", None)
        else:
            os.environ["XDG_DATA_HOME"] = self._old_xdg_data_home
        self._tmp.cleanup()

    def _write_run(
        self,
        *,
        run_id: str,
        metadata: dict,
        decisions: list[dict],
        generated: dict | None = None,
        review_template: dict | None = None,
        review_gate: dict | None = None,
        mtime: int,
    ) -> Path:
        root = Path(self._tmp.name) / "activewatcher" / "autotag" / "runs" / run_id
        root.mkdir(parents=True, exist_ok=True)
        (root / "run-metadata.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )
        (root / "autotag-decisions.jsonl").write_text(
            "\n".join(json.dumps(row) for row in decisions) + "\n",
            encoding="utf-8",
        )
        if isinstance(generated, dict):
            (root / "categories.generated.json").write_text(
                json.dumps(generated, indent=2), encoding="utf-8"
            )
        if isinstance(review_template, dict):
            (root / "review-gate.template.json").write_text(
                json.dumps(review_template, indent=2), encoding="utf-8"
            )
        if isinstance(review_gate, dict):
            (root / "review-gate.json").write_text(
                json.dumps(review_gate, indent=2), encoding="utf-8"
            )
        os.utime(root, (mtime, mtime))
        return root

    def test_list_autotag_runs_returns_latest(self) -> None:
        self._write_run(
            run_id="run_old",
            metadata={
                "created_at": "2026-02-24T10:00:00Z",
                "from_ts": "2026-02-24T09:00:00Z",
                "to_ts": "2026-02-24T10:00:00Z",
                "suggest": {
                    "categories_generated_sha256": "oldhash",
                    "pass_a": {"failed_batches": 1},
                    "pass_b": {
                        "failed_batches": 1,
                        "apply_blocked": True,
                        "apply_block_reason": "old failure",
                    },
                },
                "evaluate": {"recommend_apply": False},
            },
            decisions=[
                {"decision_type": "pass_a", "state": "unknown_candidate"},
            ],
            mtime=1,
        )
        self._write_run(
            run_id="run_new",
            metadata={
                "created_at": "2026-02-24T12:00:00Z",
                "from_ts": "2026-02-24T11:00:00Z",
                "to_ts": "2026-02-24T12:00:00Z",
                "suggest": {
                    "categories_generated_sha256": "newhash",
                    "pass_a": {"failed_batches": 0},
                    "pass_b": {
                        "failed_batches": 0,
                        "apply_blocked": False,
                        "apply_block_reason": "",
                    },
                },
                "evaluate": {"recommend_apply": True},
            },
            decisions=[
                {"decision_type": "pass_a", "state": "accepted_existing"},
                {"decision_type": "pass_b_member", "state": "proposed_new_category"},
            ],
            mtime=2,
        )

        value = reports.list_autotag_runs(limit=20)
        self.assertEqual(value.get("latest_run_id"), "run_new")
        runs_raw = value.get("runs")
        self.assertIsInstance(runs_raw, list)
        runs: list[dict[str, object]] = [
            row
            for row in (runs_raw if isinstance(runs_raw, list) else [])
            if isinstance(row, dict)
        ]
        self.assertGreaterEqual(len(runs), 2)
        self.assertEqual(runs[0].get("run_id"), "run_new")
        self.assertEqual(runs[0].get("decision_count"), 2)
        self.assertTrue(bool(runs[0].get("recommend_apply")))
        self.assertEqual(runs[1].get("run_id"), "run_old")
        self.assertEqual(runs[1].get("pass_b_apply_block_reason"), "old failure")

    def test_autotag_decisions_supports_filters_and_limit(self) -> None:
        self._write_run(
            run_id="run_filter",
            metadata={
                "from_ts": "2026-02-24T11:00:00Z",
                "to_ts": "2026-02-24T12:00:00Z",
            },
            decisions=[
                {
                    "created_at": "2026-02-24T12:00:01Z",
                    "decision_type": "pass_a",
                    "entity_id": "app:kitty",
                    "entity_type": "app",
                    "entity": "kitty",
                    "state": "accepted_existing",
                    "target_category_id": "coding",
                    "confidence": 0.91,
                    "reasons": ["terminal usage"],
                    "risk_flags": [],
                },
                {
                    "created_at": "2026-02-24T12:00:02Z",
                    "decision_type": "pass_a",
                    "entity_id": "domain:kit.edu",
                    "entity_type": "domain",
                    "entity": "kit.edu",
                    "state": "review_existing",
                    "target_category_id": "uni",
                    "confidence": 0.62,
                    "reasons": ["education domain"],
                    "risk_flags": ["weak_evidence"],
                },
                {
                    "created_at": "2026-02-24T12:00:03Z",
                    "decision_type": "pass_b_member",
                    "entity_id": "domain:youtube.com",
                    "entity_type": "domain",
                    "entity": "youtube.com",
                    "state": "proposed_new_category",
                    "target_category_id": "learning",
                    "confidence": 0.7,
                    "reasons": ["clustered unknowns"],
                    "risk_flags": [],
                },
            ],
            mtime=10,
        )

        value = reports.autotag_decisions(
            run_id="run_filter",
            decision_type="pass_a",
            state=None,
            limit=1,
        )
        self.assertEqual(value.get("run_id"), "run_filter")
        self.assertEqual(value.get("total_decision_count"), 3)
        self.assertEqual(value.get("decision_count"), 2)
        decisions_raw = value.get("decisions")
        self.assertIsInstance(decisions_raw, list)
        decisions = decisions_raw if isinstance(decisions_raw, list) else []
        self.assertEqual(len(decisions), 1)
        summary_raw = value.get("summary")
        self.assertIsInstance(summary_raw, dict)
        summary = summary_raw if isinstance(summary_raw, dict) else {}
        by_type_raw = summary.get("by_type")
        by_type = by_type_raw if isinstance(by_type_raw, dict) else {}
        self.assertEqual(by_type.get("pass_a"), 2)

    def test_autotag_decisions_empty_when_no_runs(self) -> None:
        value = reports.autotag_decisions(
            run_id=None,
            decision_type=None,
            state=None,
            limit=100,
        )
        self.assertEqual(value.get("run_id"), "")
        self.assertEqual(value.get("decision_count"), 0)
        self.assertEqual(value.get("decisions"), [])

    def test_autotag_generated_returns_latest(self) -> None:
        self._write_run(
            run_id="run_old",
            metadata={
                "from_ts": "2026-02-24T09:00:00Z",
                "to_ts": "2026-02-24T10:00:00Z",
                "suggest": {
                    "categories_generated_sha256": "oldhash",
                },
            },
            decisions=[],
            generated={"categories": [{"id": "coding"}]},
            review_template={
                "run_id": "run_old",
                "approved": False,
                "approved_by": "",
                "approved_at": "",
                "categories_generated_sha256": "oldhash",
                "allowed_category_drop_ids": [],
            },
            mtime=1,
        )
        self._write_run(
            run_id="run_new",
            metadata={
                "from_ts": "2026-02-24T11:00:00Z",
                "to_ts": "2026-02-24T12:00:00Z",
                "suggest": {
                    "categories_generated_sha256": "newhash",
                },
            },
            decisions=[],
            generated={"categories": [{"id": "coding"}, {"id": "other"}]},
            review_template={
                "run_id": "run_new",
                "approved": False,
                "approved_by": "",
                "approved_at": "",
                "categories_generated_sha256": "newhash",
                "allowed_category_drop_ids": [],
            },
            mtime=2,
        )

        value = reports.autotag_generated(run_id=None)
        self.assertEqual(value.get("run_id"), "run_new")
        self.assertEqual(value.get("from_ts"), "2026-02-24T11:00:00Z")
        self.assertEqual(value.get("to_ts"), "2026-02-24T12:00:00Z")
        self.assertEqual(value.get("categories_generated_sha256"), "newhash")
        generated_raw = value.get("generated")
        self.assertIsInstance(generated_raw, dict)
        generated = generated_raw if isinstance(generated_raw, dict) else {}
        self.assertEqual(len(generated.get("categories", [])), 2)
        review_gate_raw = value.get("review_gate")
        self.assertIsInstance(review_gate_raw, dict)
        review_gate = review_gate_raw if isinstance(review_gate_raw, dict) else {}
        self.assertEqual(review_gate.get("source"), "review-gate.template.json")
        self.assertFalse(bool(review_gate.get("approved")))

    def test_autotag_generated_empty_when_missing_file(self) -> None:
        self._write_run(
            run_id="run_no_generated",
            metadata={
                "from_ts": "2026-02-24T11:00:00Z",
                "to_ts": "2026-02-24T12:00:00Z",
                "suggest": {
                    "categories_generated_sha256": "hash",
                },
            },
            decisions=[],
            mtime=1,
        )

        value = reports.autotag_generated(run_id="run_no_generated")
        self.assertEqual(value.get("run_id"), "run_no_generated")
        self.assertEqual(value.get("categories_generated_sha256"), "hash")
        self.assertEqual(value.get("generated"), {})

    def test_autotag_generated_empty_when_no_runs(self) -> None:
        value = reports.autotag_generated(run_id=None)
        self.assertEqual(value.get("run_id"), "")
        self.assertEqual(value.get("generated"), {})
        review_gate_raw = value.get("review_gate")
        self.assertIsInstance(review_gate_raw, dict)
        review_gate = review_gate_raw if isinstance(review_gate_raw, dict) else {}
        self.assertEqual(review_gate.get("source"), "missing")

    def test_approve_autotag_review_gate_writes_gate_file(self) -> None:
        self._write_run(
            run_id="run_approve",
            metadata={
                "from_ts": "2026-02-24T11:00:00Z",
                "to_ts": "2026-02-24T12:00:00Z",
                "suggest": {
                    "categories_generated_sha256": "newhash",
                },
            },
            decisions=[],
            generated={"categories": [{"id": "coding"}, {"id": "other"}]},
            review_template={
                "run_id": "run_approve",
                "approved": False,
                "approved_by": "",
                "approved_at": "",
                "categories_generated_sha256": "newhash",
                "allowed_category_drop_ids": [],
            },
            mtime=3,
        )

        value = reports.approve_autotag_review_gate(
            run_id="run_approve",
            approved_by="leo",
            allowed_category_drop_ids=["coding", " coding ", "", "Learning"],
        )
        self.assertEqual(value.get("run_id"), "run_approve")
        gate_raw = value.get("review_gate")
        self.assertIsInstance(gate_raw, dict)
        gate = gate_raw if isinstance(gate_raw, dict) else {}
        self.assertTrue(bool(gate.get("approved")))
        self.assertEqual(gate.get("approved_by"), "leo")
        self.assertEqual(
            gate.get("allowed_category_drop_ids"),
            ["coding", "learning"],
        )
        self.assertEqual(gate.get("source"), "review-gate.json")

        root = (
            Path(self._tmp.name) / "activewatcher" / "autotag" / "runs" / "run_approve"
        )
        saved = json.loads((root / "review-gate.json").read_text(encoding="utf-8"))
        self.assertTrue(bool(saved.get("approved")))
        self.assertEqual(saved.get("approved_by"), "leo")

    def test_approve_autotag_review_gate_requires_approved_by(self) -> None:
        self._write_run(
            run_id="run_approve_invalid",
            metadata={},
            decisions=[],
            generated={"categories": [{"id": "coding"}, {"id": "other"}]},
            mtime=4,
        )
        with self.assertRaisesRegex(ValueError, "approved_by is required"):
            reports.approve_autotag_review_gate(
                run_id="run_approve_invalid",
                approved_by="",
                allowed_category_drop_ids=None,
            )


if __name__ == "__main__":
    unittest.main()
