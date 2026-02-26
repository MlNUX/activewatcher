from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .llm_client import (
    LlmContextOverflowError,
    LlmRequest,
    OllamaClient,
    render_template,
    safe_json_dump,
)
from .runtime import prompts_dir, read_json, read_jsonl, schemas_dir, write_jsonl
from .validators import (
    coerce_pass_a_payload,
    normalize_pass_a,
    parse_json_object,
    validate_schema,
)


@dataclass(frozen=True)
class PassAResult:
    decisions: list[dict[str, Any]]
    unknown_pool: list[dict[str, Any]]
    total_batches: int
    successful_batches: int
    failed_batches: int


def _existing_categories_context(
    categories: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for category in categories:
        out.append(
            {
                "id": category.get("id"),
                "label": category.get("label"),
                "apps": category.get("apps", []),
                "domains": category.get("domains", []),
                "titles": category.get("titles", []),
                "urls": category.get("urls", []),
                "title_regex": category.get("title_regex", []),
            }
        )
    return out


def _fallback_decisions(
    batch: list[dict[str, Any]], reason: str
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    decisions: list[dict[str, Any]] = []
    unknown_pool: list[dict[str, Any]] = []
    for profile in batch:
        entity_id = str(profile.get("entity_id") or "")
        if not entity_id:
            continue
        decisions.append(
            {
                "entity_id": entity_id,
                "entity_type": profile.get("entity_type"),
                "entity": profile.get("entity"),
                "target_category_id": "unknown",
                "confidence": 0.0,
                "reasons": [reason],
                "risk_flags": ["weak_evidence"],
                "token_suggestions": {
                    "apps": [],
                    "domains": [],
                    "titles": [],
                    "urls": [],
                    "title_regex": [],
                },
                "state": "unknown_candidate",
            }
        )
        unknown_pool.append(profile)
    return decisions, unknown_pool


def run_pass_a(
    *,
    run_root: Path,
    categories: list[dict[str, Any]],
    llm_client: OllamaClient,
    model: str,
    temperature: float,
    top_p: float,
    timeout_seconds: int,
    max_retries: int,
    batch_size: int,
    enable_title_regex: bool,
) -> PassAResult:
    profiles = read_jsonl(run_root / "entity-profiles.jsonl")
    if not profiles:
        return PassAResult(
            decisions=[],
            unknown_pool=[],
            total_batches=0,
            successful_batches=0,
            failed_batches=0,
        )

    schema = read_json(schemas_dir() / "autotag.classify.v1.schema.json")
    system_prompt = (prompts_dir() / "pass_a_classify.system.txt").read_text(
        encoding="utf-8"
    )
    user_template = (prompts_dir() / "pass_a_classify.user.template.txt").read_text(
        encoding="utf-8"
    )

    existing_ids = {str(c.get("id") or "") for c in categories}
    existing_context = _existing_categories_context(categories)

    rows: list[dict[str, Any]] = []
    all_decisions: dict[str, dict[str, Any]] = {}
    unknown_pool: dict[str, dict[str, Any]] = {}
    successful = 0
    failed = 0
    index = 0
    cur_batch_size = max(1, int(batch_size))
    batch_num = 0

    while index < len(profiles):
        batch = profiles[index : index + cur_batch_size]
        batch_num += 1
        profile_by_id = {
            str(p.get("entity_id") or ""): p
            for p in batch
            if str(p.get("entity_id") or "")
        }

        prompt_values = {
            "MIN_CONFIDENCE_AUTO_ACCEPT": "0.78",
            "ENABLE_TITLE_REGEX": "true" if enable_title_regex else "false",
            "EXISTING_CATEGORIES_JSON": safe_json_dump(existing_context),
            "ENTITY_PROFILES_JSON": safe_json_dump(batch),
        }
        user_prompt = render_template(user_template, prompt_values)
        request = LlmRequest(
            model=model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            temperature=temperature,
            top_p=top_p,
            timeout_seconds=timeout_seconds,
            max_retries=max_retries,
        )

        raw_response = ""
        batch_ok = False
        error_text = ""

        try:
            raw_response = llm_client.complete_json(request)
            parsed = parse_json_object(raw_response)
            coerced = coerce_pass_a_payload(
                payload=parsed,
                profile_by_id=profile_by_id,
                enable_title_regex=enable_title_regex,
            )
            validate_schema(coerced, schema)
            normalized, unknown_batch = normalize_pass_a(
                payload=coerced,
                profile_by_id=profile_by_id,
                existing_category_ids=existing_ids,
                enable_title_regex=enable_title_regex,
            )
            for decision in normalized:
                entity_id = str(decision.get("entity_id") or "")
                if entity_id:
                    all_decisions[entity_id] = decision
            for profile in unknown_batch:
                entity_id = str(profile.get("entity_id") or "")
                if entity_id:
                    unknown_pool[entity_id] = profile
            successful += 1
            batch_ok = True
            index += len(batch)
        except LlmContextOverflowError:
            if cur_batch_size > 4:
                cur_batch_size = max(4, cur_batch_size // 2)
                batch_num -= 1
                continue
            fallback_decisions, fallback_unknown = _fallback_decisions(
                batch, "pass-a context overflow"
            )
            for decision in fallback_decisions:
                all_decisions[str(decision["entity_id"])] = decision
            for profile in fallback_unknown:
                unknown_pool[str(profile["entity_id"])] = profile
            failed += 1
            error_text = "context overflow"
            index += len(batch)
        except Exception as first_error:
            try:
                repair_prompt = (
                    user_prompt
                    + "\n\nREPAIR INSTRUCTION: Return strict JSON only. No prose. Must match autotag.classify.v1 exactly."
                )
                repair_request = LlmRequest(
                    model=model,
                    system_prompt=system_prompt,
                    user_prompt=repair_prompt,
                    temperature=temperature,
                    top_p=top_p,
                    timeout_seconds=timeout_seconds,
                    max_retries=max_retries,
                )
                raw_response = llm_client.complete_json(repair_request)
                parsed = parse_json_object(raw_response)
                coerced = coerce_pass_a_payload(
                    payload=parsed,
                    profile_by_id=profile_by_id,
                    enable_title_regex=enable_title_regex,
                )
                validate_schema(coerced, schema)
                normalized, unknown_batch = normalize_pass_a(
                    payload=coerced,
                    profile_by_id=profile_by_id,
                    existing_category_ids=existing_ids,
                    enable_title_regex=enable_title_regex,
                )
                for decision in normalized:
                    entity_id = str(decision.get("entity_id") or "")
                    if entity_id:
                        all_decisions[entity_id] = decision
                for profile in unknown_batch:
                    entity_id = str(profile.get("entity_id") or "")
                    if entity_id:
                        unknown_pool[entity_id] = profile
                successful += 1
                batch_ok = True
            except Exception as repair_error:
                fallback_decisions, fallback_unknown = _fallback_decisions(
                    batch, "pass-a batch failed"
                )
                for decision in fallback_decisions:
                    all_decisions[str(decision["entity_id"])] = decision
                for profile in fallback_unknown:
                    unknown_pool[str(profile["entity_id"])] = profile
                failed += 1
                error_text = f"{first_error}; repair_failed={repair_error}"
            finally:
                index += len(batch)

        rows.append(
            {
                "pass": "a",
                "batch": batch_num,
                "batch_size": len(batch),
                "entity_ids": sorted(profile_by_id.keys()),
                "ok": batch_ok,
                "error": error_text,
                "response": raw_response,
            }
        )

    write_jsonl(run_root / "pass-a.raw.jsonl", rows)
    decisions = sorted(
        all_decisions.values(), key=lambda d: str(d.get("entity_id") or "")
    )
    unknown = sorted(unknown_pool.values(), key=lambda p: str(p.get("entity_id") or ""))
    return PassAResult(
        decisions=decisions,
        unknown_pool=unknown,
        total_batches=successful + failed,
        successful_batches=successful,
        failed_batches=failed,
    )
