from __future__ import annotations

import unittest

from activewatcher_autotag.validators import (
    coerce_pass_a_payload,
    coerce_pass_b_payload,
    validate_pass_b_proposals,
)


class CoercePassAPayloadTests(unittest.TestCase):
    def test_coerce_legacy_category_id_and_tokens(self) -> None:
        profile_by_id = {
            "app:kitty": {
                "entity_id": "app:kitty",
                "entity_type": "app",
                "entity": "kitty",
            }
        }
        payload = {
            "items": [
                {
                    "entity_id": "app:kitty",
                    "category_id": "coding",
                    "confidence": 0.81,
                    "reasons": ["terminal used for coding"],
                    "titles": ["vim"],
                }
            ]
        }

        coerced = coerce_pass_a_payload(
            payload=payload,
            profile_by_id=profile_by_id,
            enable_title_regex=False,
        )

        self.assertEqual(coerced.get("version"), "autotag.classify.v1")
        items_raw = coerced.get("items")
        if not isinstance(items_raw, list):
            self.fail("items must be a list")
            return
        items = items_raw
        self.assertEqual(len(items), 1)
        row = items[0]
        self.assertEqual(row.get("target_category_id"), "coding")
        self.assertEqual(row.get("entity_type"), "app")
        token_suggestions = row.get("token_suggestions")
        self.assertIsInstance(token_suggestions, dict)
        self.assertEqual(token_suggestions.get("titles"), ["vim"])
        self.assertEqual(token_suggestions.get("title_regex"), [])


class CoercePassBPayloadTests(unittest.TestCase):
    def test_coerce_legacy_rule_token_shape_and_nearest_existing(self) -> None:
        batch_profiles = [
            {
                "entity_id": "app:kitty",
                "entity_type": "app",
                "entity": "kitty",
                "seconds": 1000,
                "active_days": 2,
            },
            {
                "entity_id": "domain:kit.edu",
                "entity_type": "domain",
                "entity": "kit.edu",
                "seconds": 2000,
                "active_days": 3,
            },
        ]
        payload = {
            "proposals": [
                {
                    "id": "education",
                    "label": "Education",
                    "apps": ["kitty"],
                    "domains": ["kit.edu"],
                    "coverage": {
                        "unique_apps": 1,
                        "unique_domains": 1,
                        "combined": 2,
                        "total_seconds": 3000,
                        "active_days": 3,
                    },
                    "nearest_existing": [
                        {
                            "id": "uni",
                            "similarity": 0.8,
                            "reason": "close match",
                        }
                    ],
                }
            ]
        }

        coerced = coerce_pass_b_payload(
            payload=payload,
            batch_profiles=batch_profiles,
            enable_title_regex=False,
        )

        self.assertEqual(coerced.get("version"), "autotag.propose.v1")
        proposals_raw = coerced.get("proposals")
        if not isinstance(proposals_raw, list):
            self.fail("proposals must be a list")
            return
        proposals = proposals_raw
        self.assertEqual(len(proposals), 1)

        proposal = proposals[0]
        self.assertEqual(proposal.get("id"), "education")
        members = proposal.get("members")
        self.assertIsInstance(members, list)
        self.assertEqual(len(members), 2)
        nearest = proposal.get("nearest_existing")
        self.assertIsInstance(nearest, list)
        self.assertEqual(nearest[0].get("category_id"), "uni")
        rule_tokens = proposal.get("rule_tokens")
        self.assertIsInstance(rule_tokens, dict)
        self.assertEqual(rule_tokens.get("apps"), ["kitty"])
        self.assertEqual(rule_tokens.get("domains"), ["kit.edu"])

    def test_coerce_pass_b_uses_profile_coverage_not_model_coverage(self) -> None:
        batch_profiles = [
            {
                "entity_id": "app:kitty",
                "entity_type": "app",
                "entity": "kitty",
                "seconds": 1000,
                "active_days": 2,
            },
            {
                "entity_id": "domain:kit.edu",
                "entity_type": "domain",
                "entity": "kit.edu",
                "seconds": 2000,
                "active_days": 3,
            },
        ]
        payload = {
            "proposals": [
                {
                    "id": "education",
                    "label": "Education",
                    "apps": ["kitty"],
                    "domains": ["kit.edu"],
                    "coverage": {
                        "unique_apps": 1,
                        "unique_domains": 1,
                        "combined": 2,
                        "total_seconds": 999999,
                        "active_days": 999,
                    },
                }
            ]
        }

        coerced = coerce_pass_b_payload(
            payload=payload,
            batch_profiles=batch_profiles,
            enable_title_regex=False,
        )
        proposals = coerced.get("proposals")
        if not isinstance(proposals, list):
            self.fail("proposals must be a list")
            return
        self.assertEqual(len(proposals), 1)
        proposal = proposals[0]
        coverage = proposal.get("coverage")
        self.assertIsInstance(coverage, dict)
        self.assertEqual(coverage.get("total_seconds"), 3000.0)
        self.assertEqual(coverage.get("active_days"), 3)


class ValidatePassBProposalsTests(unittest.TestCase):
    def test_rejects_duplicate_proposal_ids(self) -> None:
        proposals = [
            {
                "id": "learning",
                "label": "Learning",
                "members": [
                    {
                        "entity_id": "app:one",
                        "entity_type": "app",
                        "entity": "one",
                        "confidence": 0.8,
                    }
                ],
                "coverage": {
                    "unique_apps": 1,
                    "unique_domains": 0,
                    "combined": 1,
                    "total_seconds": 10,
                    "active_days": 1,
                },
                "cohesion_score": 0.8,
                "rule_tokens": {},
            },
            {
                "id": "learning",
                "label": "Learning 2",
                "members": [
                    {
                        "entity_id": "app:two",
                        "entity_type": "app",
                        "entity": "two",
                        "confidence": 0.8,
                    }
                ],
                "coverage": {
                    "unique_apps": 1,
                    "unique_domains": 0,
                    "combined": 1,
                    "total_seconds": 10,
                    "active_days": 1,
                },
                "cohesion_score": 0.8,
                "rule_tokens": {},
            },
        ]

        _accepted, rejected = validate_pass_b_proposals(
            proposals=proposals,
            existing_categories=[
                {"id": "other", "apps": [], "domains": [], "titles": [], "urls": []}
            ],
            pass_a_decisions=[],
            enable_title_regex=False,
        )

        reasons = {
            str(row.get("reason") or "") for row in rejected if isinstance(row, dict)
        }
        self.assertIn("duplicate proposal id", reasons)


if __name__ == "__main__":
    unittest.main()
