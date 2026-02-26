from __future__ import annotations

import json
import re
from statistics import fmean
from typing import Any

from .merge_rules import TOKEN_FIELDS, category_tokens, sanitize_tokens
from .settings import THRESHOLDS

_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,31}$")
_BLOCKING_RISK_FLAGS = {"ambiguous", "mixed_intent"}


class SchemaValidationError(ValueError):
    pass


def parse_json_object(raw: str) -> dict[str, Any]:
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("response is not a JSON object")
    return value


def validate_schema(payload: dict[str, Any], schema: dict[str, Any]) -> None:
    try:
        import jsonschema  # type: ignore
    except ImportError as e:
        raise RuntimeError("Missing dependency: jsonschema") from e
    validator = jsonschema.Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(payload), key=lambda e: list(e.path))
    if errors:
        first = errors[0]
        path = ".".join(str(p) for p in first.path)
        raise SchemaValidationError(
            f"schema validation failed at '{path}': {first.message}"
        )


def _clamp_confidence(value: Any) -> float:
    try:
        n = float(value)
    except Exception:
        return 0.0
    if n < 0:
        return 0.0
    if n > 1:
        return 1.0
    return n


def _normalize_token_suggestions(
    value: Any, *, enable_title_regex: bool
) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {field: [] for field in TOKEN_FIELDS}
    return sanitize_tokens(value, enable_title_regex=enable_title_regex)


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if str(v).strip()]
    if isinstance(value, str):
        s = value.strip()
        return [s] if s else []
    return []


def coerce_pass_a_payload(
    *,
    payload: dict[str, Any],
    profile_by_id: dict[str, dict[str, Any]],
    enable_title_regex: bool,
) -> dict[str, Any]:
    candidates = [
        payload.get("items"),
        payload.get("classifications"),
        payload.get("results"),
        payload.get("entities"),
    ]
    items_raw: list[Any] = []
    for candidate in candidates:
        if isinstance(candidate, list):
            items_raw = candidate
            break

    out_items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for raw in items_raw:
        if not isinstance(raw, dict):
            continue
        entity_id = str(raw.get("entity_id") or raw.get("id") or "").strip()
        if not entity_id or entity_id in seen_ids:
            continue

        profile = profile_by_id.get(entity_id, {})
        entity_type = str(
            raw.get("entity_type") or profile.get("entity_type") or ""
        ).strip()
        if entity_type not in {"app", "domain"} and ":" in entity_id:
            prefix = entity_id.split(":", 1)[0].strip().lower()
            if prefix in {"app", "domain"}:
                entity_type = prefix
        if entity_type not in {"app", "domain"}:
            entity_type = str(profile.get("entity_type") or "app")

        entity = str(raw.get("entity") or profile.get("entity") or "").strip()
        if not entity:
            continue

        target_category_id = str(
            raw.get("target_category_id")
            or raw.get("category_id")
            or raw.get("category")
            or raw.get("target")
            or "unknown"
        ).strip()

        reasons = _string_list(raw.get("reasons"))
        if not reasons:
            reasons = _string_list(raw.get("reason"))
        if not reasons:
            reasons = ["insufficient evidence"]

        risk_flags = sorted({x for x in _string_list(raw.get("risk_flags")) if x})
        if not risk_flags:
            risk_flags = sorted({x for x in _string_list(raw.get("flags")) if x})

        token_suggestions_raw = raw.get("token_suggestions")
        if not isinstance(token_suggestions_raw, dict):
            token_suggestions_raw = {}
        if not token_suggestions_raw:
            legacy_tokens = {
                field: raw.get(field)
                for field in TOKEN_FIELDS
                if raw.get(field) is not None
            }
            if legacy_tokens:
                token_suggestions_raw = legacy_tokens

        out_items.append(
            {
                "entity_id": entity_id,
                "entity_type": entity_type,
                "entity": entity,
                "target_category_id": target_category_id or "unknown",
                "confidence": _clamp_confidence(raw.get("confidence")),
                "reasons": reasons[:3],
                "risk_flags": risk_flags,
                "token_suggestions": _normalize_token_suggestions(
                    token_suggestions_raw, enable_title_regex=enable_title_regex
                ),
            }
        )
        seen_ids.add(entity_id)

    if not out_items and profile_by_id:
        for entity_id, profile in sorted(profile_by_id.items()):
            out_items.append(
                {
                    "entity_id": entity_id,
                    "entity_type": str(profile.get("entity_type") or "app"),
                    "entity": str(profile.get("entity") or entity_id),
                    "target_category_id": "unknown",
                    "confidence": 0.0,
                    "reasons": ["missing from pass-a output"],
                    "risk_flags": ["weak_evidence"],
                    "token_suggestions": {field: [] for field in TOKEN_FIELDS},
                }
            )

    return {
        "version": "autotag.classify.v1",
        "items": out_items,
    }


def coerce_pass_b_payload(
    *,
    payload: dict[str, Any],
    batch_profiles: list[dict[str, Any]],
    enable_title_regex: bool,
) -> dict[str, Any]:
    profile_by_id = {
        str(p.get("entity_id") or ""): p
        for p in batch_profiles
        if isinstance(p, dict) and str(p.get("entity_id") or "")
    }

    candidates = [
        payload.get("proposals"),
        payload.get("items"),
        payload.get("categories"),
        payload.get("new_categories"),
    ]
    proposals_raw: list[Any] = []
    for candidate in candidates:
        if isinstance(candidate, list):
            proposals_raw = candidate
            break

    out_proposals: list[dict[str, Any]] = []
    assigned_ids: set[str] = set()

    for raw in proposals_raw:
        if not isinstance(raw, dict):
            continue
        proposal_id = str(raw.get("id") or "").strip().lower()
        if not proposal_id:
            continue
        label = str(raw.get("label") or proposal_id).strip() or proposal_id

        rule_tokens_raw = raw.get("rule_tokens")
        if not isinstance(rule_tokens_raw, dict):
            rule_tokens_raw = {
                field: raw.get(field)
                for field in TOKEN_FIELDS
                if raw.get(field) is not None
            }
        rule_tokens = sanitize_tokens(
            rule_tokens_raw, enable_title_regex=enable_title_regex
        )

        members_raw = raw.get("members") if isinstance(raw.get("members"), list) else []
        members: list[dict[str, Any]] = []
        member_ids: set[str] = set()

        for member in members_raw:
            if not isinstance(member, dict):
                continue
            entity_id = str(member.get("entity_id") or "").strip()
            if not entity_id or entity_id in member_ids:
                continue
            profile = profile_by_id.get(entity_id, {})
            entity_type = (
                str(member.get("entity_type") or profile.get("entity_type") or "")
                .strip()
                .lower()
            )
            entity = str(member.get("entity") or profile.get("entity") or "").strip()
            if entity_type not in {"app", "domain"} or not entity:
                continue
            members.append(
                {
                    "entity_id": entity_id,
                    "entity_type": entity_type,
                    "entity": entity,
                    "confidence": _clamp_confidence(
                        member.get("confidence") or member.get("score")
                    ),
                }
            )
            member_ids.add(entity_id)

        if not members:
            apps = {x.lower().strip() for x in rule_tokens.get("apps", []) if x}
            domains = {x.lower().strip() for x in rule_tokens.get("domains", []) if x}
            for profile in profile_by_id.values():
                entity_id = str(profile.get("entity_id") or "").strip()
                entity_type = str(profile.get("entity_type") or "").strip().lower()
                entity = str(profile.get("entity") or "").strip()
                if not entity_id or entity_id in member_ids:
                    continue
                key = entity.lower().strip()
                if entity_type == "app" and key in apps:
                    members.append(
                        {
                            "entity_id": entity_id,
                            "entity_type": "app",
                            "entity": entity,
                            "confidence": 0.7,
                        }
                    )
                    member_ids.add(entity_id)
                elif entity_type == "domain" and key in domains:
                    members.append(
                        {
                            "entity_id": entity_id,
                            "entity_type": "domain",
                            "entity": entity,
                            "confidence": 0.7,
                        }
                    )
                    member_ids.add(entity_id)

        if not members:
            continue

        assigned_ids.update(member_ids)

        unique_apps = len(
            {
                str(m.get("entity") or "").strip().lower()
                for m in members
                if str(m.get("entity_type") or "") == "app"
            }
        )
        unique_domains = len(
            {
                str(m.get("entity") or "").strip().lower()
                for m in members
                if str(m.get("entity_type") or "") == "domain"
            }
        )
        combined = unique_apps + unique_domains

        profile_seconds = 0.0
        profile_days = 0
        for member in members:
            profile = profile_by_id.get(str(member.get("entity_id") or ""), {})
            try:
                profile_seconds += float(profile.get("seconds") or 0.0)
            except Exception:
                pass
            try:
                profile_days = max(profile_days, int(profile.get("active_days") or 0))
            except Exception:
                pass

        coverage_raw = (
            raw.get("coverage") if isinstance(raw.get("coverage"), dict) else {}
        )
        total_seconds = float(coverage_raw.get("total_seconds") or profile_seconds)
        active_days = int(coverage_raw.get("active_days") or profile_days)

        nearest_raw = (
            raw.get("nearest_existing")
            if isinstance(raw.get("nearest_existing"), list)
            else []
        )
        nearest_existing: list[dict[str, Any]] = []
        for row in nearest_raw:
            if not isinstance(row, dict):
                continue
            category_id = str(row.get("category_id") or row.get("id") or "").strip()
            if not category_id:
                continue
            nearest_existing.append(
                {
                    "category_id": category_id,
                    "similarity": _clamp_confidence(row.get("similarity")),
                    "reason": str(
                        row.get("reason") or "legacy nearest_existing row"
                    ).strip()[:140],
                }
            )

        out_proposals.append(
            {
                "id": proposal_id,
                "label": label,
                "description": str(
                    raw.get("description")
                    or f"Auto-generated category proposal '{label}' from unknown entities"
                ).strip()[:220],
                "members": members,
                "coverage": {
                    "unique_apps": unique_apps,
                    "unique_domains": unique_domains,
                    "combined": combined,
                    "total_seconds": max(0.0, total_seconds),
                    "active_days": max(0, active_days),
                },
                "cohesion_score": _clamp_confidence(
                    raw.get("cohesion_score")
                    or raw.get("cohesion")
                    or THRESHOLDS.new_category_min_cohesion_score
                ),
                "not_subcategory_reason": str(
                    raw.get("not_subcategory_reason")
                    or "Compatibility normalization from legacy pass-b format"
                ).strip()[:220],
                "nearest_existing": nearest_existing[:3],
                "rule_tokens": rule_tokens,
            }
        )

    left_raw = payload.get("left_unassigned_entity_ids")
    if not isinstance(left_raw, list):
        left_raw = (
            payload.get("left_unassigned")
            if isinstance(payload.get("left_unassigned"), list)
            else []
        )
    left_unassigned = {str(v).strip() for v in left_raw if str(v).strip()}

    for entity_id in profile_by_id:
        if entity_id not in assigned_ids:
            left_unassigned.add(entity_id)

    return {
        "version": "autotag.propose.v1",
        "proposals": out_proposals,
        "left_unassigned_entity_ids": sorted(left_unassigned),
    }


def normalize_pass_a(
    *,
    payload: dict[str, Any],
    profile_by_id: dict[str, dict[str, Any]],
    existing_category_ids: set[str],
    enable_title_regex: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    items = payload.get("items")
    if not isinstance(items, list):
        raise ValueError("pass-a payload missing items")

    decisions: list[dict[str, Any]] = []
    unknown_pool: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for item in items:
        if not isinstance(item, dict):
            continue
        entity_id = str(item.get("entity_id") or "").strip()
        if not entity_id or entity_id in seen_ids or entity_id not in profile_by_id:
            continue
        seen_ids.add(entity_id)
        profile = profile_by_id[entity_id]
        entity_type = str(item.get("entity_type") or profile.get("entity_type") or "")
        entity = str(item.get("entity") or profile.get("entity") or "")
        target_id = str(item.get("target_category_id") or "unknown").strip().lower()
        confidence = _clamp_confidence(item.get("confidence"))
        reasons = item.get("reasons") if isinstance(item.get("reasons"), list) else []
        reasons_out = [str(r).strip() for r in reasons if str(r).strip()][:3] or [
            "insufficient evidence"
        ]
        risk_flags_raw = (
            item.get("risk_flags") if isinstance(item.get("risk_flags"), list) else []
        )
        risk_flags = sorted({str(x).strip() for x in risk_flags_raw if str(x).strip()})
        token_suggestions = _normalize_token_suggestions(
            item.get("token_suggestions"), enable_title_regex=enable_title_regex
        )

        if target_id != "unknown" and target_id not in existing_category_ids:
            target_id = "unknown"
            risk_flags = sorted(set(risk_flags) | {"weak_evidence"})
            reasons_out = reasons_out + ["invalid target category id"]

        blocking = any(flag in _BLOCKING_RISK_FLAGS for flag in risk_flags)
        if (
            target_id != "unknown"
            and confidence >= THRESHOLDS.classify_auto_accept_min_confidence
            and not blocking
        ):
            state = "accepted_existing"
        elif (
            target_id != "unknown"
            and confidence >= THRESHOLDS.classify_review_min_confidence
        ):
            state = "review_existing"
        else:
            state = "unknown_candidate"
            target_id = "unknown"

        row = {
            "entity_id": entity_id,
            "entity_type": entity_type,
            "entity": entity,
            "target_category_id": target_id,
            "confidence": round(confidence, 4),
            "reasons": reasons_out,
            "risk_flags": risk_flags,
            "token_suggestions": token_suggestions,
            "state": state,
        }
        decisions.append(row)
        if state == "unknown_candidate" or (
            state == "review_existing"
            and confidence < THRESHOLDS.unknown_pool_review_cutoff
        ):
            unknown_pool.append(profile)

    for entity_id, profile in profile_by_id.items():
        if entity_id in seen_ids:
            continue
        row = {
            "entity_id": entity_id,
            "entity_type": profile.get("entity_type"),
            "entity": profile.get("entity"),
            "target_category_id": "unknown",
            "confidence": 0.0,
            "reasons": ["missing from pass-a output"],
            "risk_flags": ["weak_evidence"],
            "token_suggestions": {field: [] for field in TOKEN_FIELDS},
            "state": "unknown_candidate",
        }
        decisions.append(row)
        unknown_pool.append(profile)

    decisions.sort(key=lambda d: str(d.get("entity_id") or ""))
    dedup_unknown: dict[str, dict[str, Any]] = {}
    for profile in unknown_pool:
        entity_id = str(profile.get("entity_id") or "")
        if entity_id and entity_id not in dedup_unknown:
            dedup_unknown[entity_id] = profile
    return decisions, list(dedup_unknown.values())


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left and not right:
        return 0.0
    union = left | right
    if not union:
        return 0.0
    return len(left & right) / len(union)


def validate_pass_b_proposals(
    *,
    proposals: list[dict[str, Any]],
    existing_categories: list[dict[str, Any]],
    pass_a_decisions: list[dict[str, Any]],
    enable_title_regex: bool,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    existing_by_id = {str(c.get("id") or ""): c for c in existing_categories}
    existing_ids = set(existing_by_id.keys())
    existing_token_sets = {
        cat_id: category_tokens(cat) for cat_id, cat in existing_by_id.items()
    }
    accepted_lookup = {
        str(row.get("entity_id") or ""): str(row.get("target_category_id") or "")
        for row in pass_a_decisions
        if str(row.get("state") or "") == "accepted_existing"
    }

    accepted: list[dict[str, Any]] = []
    rejected: list[dict[str, Any]] = []

    for raw in proposals:
        if not isinstance(raw, dict):
            continue
        proposal_id = str(raw.get("id") or "").strip().lower()
        label = str(raw.get("label") or proposal_id).strip() or proposal_id
        description = str(raw.get("description") or "").strip()
        if not _ID_RE.fullmatch(proposal_id) or proposal_id == "other":
            rejected.append(
                {"id": proposal_id or "<empty>", "reason": "invalid proposal id"}
            )
            continue

        members_raw = raw.get("members")
        if not isinstance(members_raw, list) or not members_raw:
            rejected.append({"id": proposal_id, "reason": "missing members"})
            continue

        members: list[dict[str, Any]] = []
        member_ids: set[str] = set()
        unique_apps: set[str] = set()
        unique_domains: set[str] = set()
        member_conf: list[float] = []
        for member in members_raw:
            if not isinstance(member, dict):
                continue
            entity_id = str(member.get("entity_id") or "").strip()
            entity_type = str(member.get("entity_type") or "").strip()
            entity = str(member.get("entity") or "").strip()
            conf = _clamp_confidence(member.get("confidence"))
            if not entity_id or entity_id in member_ids:
                continue
            if entity_type not in {"app", "domain"}:
                continue
            member_ids.add(entity_id)
            if entity_type == "app":
                unique_apps.add(entity)
            else:
                unique_domains.add(entity)
            member_conf.append(conf)
            members.append(
                {
                    "entity_id": entity_id,
                    "entity_type": entity_type,
                    "entity": entity,
                    "confidence": round(conf, 4),
                }
            )

        if not members:
            rejected.append({"id": proposal_id, "reason": "no valid members"})
            continue

        coverage = raw.get("coverage") if isinstance(raw.get("coverage"), dict) else {}
        cov_apps = int(coverage.get("unique_apps") or 0)
        cov_domains = int(coverage.get("unique_domains") or 0)
        cov_combined = int(coverage.get("combined") or 0)
        cov_seconds = float(coverage.get("total_seconds") or 0.0)
        cov_days = int(coverage.get("active_days") or 0)

        recomputed_apps = len(unique_apps)
        recomputed_domains = len(unique_domains)
        recomputed_combined = recomputed_apps + recomputed_domains

        if cov_combined != cov_apps + cov_domains:
            rejected.append({"id": proposal_id, "reason": "coverage.combined mismatch"})
            continue
        if (
            cov_apps != recomputed_apps
            or cov_domains != recomputed_domains
            or cov_combined != recomputed_combined
        ):
            rejected.append(
                {"id": proposal_id, "reason": "coverage does not match members"}
            )
            continue
        if cov_combined < THRESHOLDS.new_category_min_combined_entities:
            rejected.append(
                {"id": proposal_id, "reason": "combined entities below threshold"}
            )
            continue
        if cov_seconds < THRESHOLDS.new_category_min_total_seconds:
            rejected.append(
                {"id": proposal_id, "reason": "total_seconds below threshold"}
            )
            continue
        if cov_days < THRESHOLDS.new_category_min_active_days:
            rejected.append(
                {"id": proposal_id, "reason": "active_days below threshold"}
            )
            continue

        avg_member_confidence = float(fmean(member_conf)) if member_conf else 0.0
        if avg_member_confidence < THRESHOLDS.new_category_min_avg_member_confidence:
            rejected.append(
                {"id": proposal_id, "reason": "avg_member_confidence below threshold"}
            )
            continue

        cohesion_score = _clamp_confidence(raw.get("cohesion_score"))
        if cohesion_score < THRESHOLDS.new_category_min_cohesion_score:
            rejected.append(
                {"id": proposal_id, "reason": "cohesion_score below threshold"}
            )
            continue

        rule_tokens = sanitize_tokens(
            raw.get("rule_tokens"), enable_title_regex=enable_title_regex
        )
        proposal_token_set: set[str] = set()
        for field in TOKEN_FIELDS:
            proposal_token_set.update(
                {x.lower().strip() for x in rule_tokens.get(field, []) if x}
            )

        nearest_rows: list[dict[str, Any]] = []
        blocked = False
        blocked_reason = ""
        for existing_id in sorted(existing_ids):
            member_matches = sum(
                1
                for member_id in member_ids
                if accepted_lookup.get(member_id) == existing_id
            )
            containment = member_matches / len(member_ids) if member_ids else 0.0
            token_jaccard = _jaccard(
                proposal_token_set, existing_token_sets.get(existing_id, set())
            )
            similarity = max(token_jaccard, containment)
            nearest_rows.append(
                {
                    "category_id": existing_id,
                    "containment": round(containment, 4),
                    "similarity": round(similarity, 4),
                }
            )
            if (
                similarity >= THRESHOLDS.subcategory_similarity_block_threshold
                and containment >= THRESHOLDS.subcategory_containment_block_threshold
            ) or containment >= THRESHOLDS.subcategory_containment_hard_block_threshold:
                blocked = True
                blocked_reason = f"subcategory guard blocked by {existing_id}"

        nearest_rows.sort(
            key=lambda row: (
                -row["containment"],
                -row["similarity"],
                row["category_id"],
            )
        )
        nearest_top = [
            {
                "category_id": row["category_id"],
                "similarity": row["similarity"],
                "reason": "deterministic nearest category",
            }
            for row in nearest_rows[:3]
        ]

        if blocked:
            rejected.append({"id": proposal_id, "reason": blocked_reason})
            continue

        accepted.append(
            {
                "id": proposal_id,
                "label": label,
                "description": description,
                "members": members,
                "coverage": {
                    "unique_apps": cov_apps,
                    "unique_domains": cov_domains,
                    "combined": cov_combined,
                    "total_seconds": round(cov_seconds, 3),
                    "active_days": cov_days,
                },
                "avg_member_confidence": round(avg_member_confidence, 4),
                "cohesion_score": round(cohesion_score, 4),
                "nearest_existing": nearest_top,
                "not_subcategory_reason": str(
                    raw.get("not_subcategory_reason") or ""
                ).strip(),
                "rule_tokens": rule_tokens,
            }
        )

    accepted.sort(
        key=lambda row: (
            -row["coverage"]["combined"],
            -row["coverage"]["total_seconds"],
            row["id"],
        )
    )
    if len(accepted) > THRESHOLDS.max_new_categories:
        overflow = accepted[THRESHOLDS.max_new_categories :]
        for row in overflow:
            rejected.append({"id": row["id"], "reason": "max_new_categories reached"})
        accepted = accepted[: THRESHOLDS.max_new_categories]

    return accepted, rejected
