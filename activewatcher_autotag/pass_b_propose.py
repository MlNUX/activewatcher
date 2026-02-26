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
from .runtime import prompts_dir, read_json, schemas_dir, write_jsonl
from .settings import THRESHOLDS
from .validators import (
    coerce_pass_b_payload,
    parse_json_object,
    validate_pass_b_proposals,
    validate_schema,
)


@dataclass(frozen=True)
class PassBResult:
    status: str
    proposals: list[dict[str, Any]]
    rejected: list[dict[str, Any]]
    left_unassigned_entity_ids: list[str]
    total_batches: int
    successful_batches: int
    failed_batches: int
    success_ratio: float
    apply_blocked: bool
    apply_block_reason: str


def run_pass_b(
    *,
    run_root: Path,
    unknown_pool: list[dict[str, Any]],
    categories: list[dict[str, Any]],
    pass_a_decisions: list[dict[str, Any]],
    llm_client: OllamaClient,
    model: str,
    temperature: float,
    top_p: float,
    timeout_seconds: int,
    max_retries: int,
    batch_size: int,
    enable_title_regex: bool,
) -> PassBResult:
    schema = read_json(schemas_dir() / "autotag.propose.v1.schema.json")
    system_prompt = (prompts_dir() / "pass_b_propose.system.txt").read_text(
        encoding="utf-8"
    )
    user_template = (prompts_dir() / "pass_b_propose.user.template.txt").read_text(
        encoding="utf-8"
    )

    rows: list[dict[str, Any]] = []
    if not unknown_pool:
        write_jsonl(run_root / "pass-b.raw.jsonl", rows)
        return PassBResult(
            status="ok",
            proposals=[],
            rejected=[],
            left_unassigned_entity_ids=[],
            total_batches=0,
            successful_batches=0,
            failed_batches=0,
            success_ratio=1.0,
            apply_blocked=False,
            apply_block_reason="",
        )

    proposed_raw: list[dict[str, Any]] = []
    left_unassigned: set[str] = set()
    successful = 0
    failed = 0
    index = 0
    batch_num = 0
    cur_batch_size = max(1, int(batch_size))

    while index < len(unknown_pool):
        batch = unknown_pool[index : index + cur_batch_size]
        batch_num += 1
        entity_ids = [str(x.get("entity_id") or "") for x in batch]

        prompt_values = {
            "NEW_CATEGORY_MIN_COMBINED": str(
                THRESHOLDS.new_category_min_combined_entities
            ),
            "NEW_CATEGORY_MIN_TOTAL_SECONDS": str(
                int(THRESHOLDS.new_category_min_total_seconds)
            ),
            "NEW_CATEGORY_MIN_ACTIVE_DAYS": str(
                THRESHOLDS.new_category_min_active_days
            ),
            "MAX_NEW_CATEGORIES": str(THRESHOLDS.max_new_categories),
            "ENABLE_TITLE_REGEX": "true" if enable_title_regex else "false",
            "EXISTING_CATEGORIES_JSON": safe_json_dump(categories),
            "UNKNOWN_ENTITY_PROFILES_JSON": safe_json_dump(batch),
            "CLUSTER_HINTS_JSON": "[]",
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
            coerced = coerce_pass_b_payload(
                payload=parsed,
                batch_profiles=batch,
                enable_title_regex=enable_title_regex,
            )
            validate_schema(coerced, schema)
            proposals = (
                coerced.get("proposals")
                if isinstance(coerced.get("proposals"), list)
                else []
            )
            proposed_raw.extend([x for x in proposals if isinstance(x, dict)])
            left = coerced.get("left_unassigned_entity_ids")
            if isinstance(left, list):
                for entity_id in left:
                    s = str(entity_id or "").strip()
                    if s:
                        left_unassigned.add(s)
            successful += 1
            batch_ok = True
            index += len(batch)
        except LlmContextOverflowError:
            if cur_batch_size > 4:
                cur_batch_size = max(4, cur_batch_size // 2)
                batch_num -= 1
                continue
            failed += 1
            error_text = "context overflow"
            index += len(batch)
            left_unassigned.update([x for x in entity_ids if x])
        except Exception as first_error:
            try:
                repair_prompt = (
                    user_prompt
                    + "\n\nREPAIR INSTRUCTION: Return strict JSON only. No prose. Must match autotag.propose.v1 exactly."
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
                coerced = coerce_pass_b_payload(
                    payload=parsed,
                    batch_profiles=batch,
                    enable_title_regex=enable_title_regex,
                )
                validate_schema(coerced, schema)
                proposals = (
                    coerced.get("proposals")
                    if isinstance(coerced.get("proposals"), list)
                    else []
                )
                proposed_raw.extend([x for x in proposals if isinstance(x, dict)])
                left = coerced.get("left_unassigned_entity_ids")
                if isinstance(left, list):
                    for entity_id in left:
                        s = str(entity_id or "").strip()
                        if s:
                            left_unassigned.add(s)
                successful += 1
                batch_ok = True
            except Exception as repair_error:
                failed += 1
                error_text = f"{first_error}; repair_failed={repair_error}"
                left_unassigned.update([x for x in entity_ids if x])
            finally:
                index += len(batch)

        rows.append(
            {
                "pass": "b",
                "batch": batch_num,
                "batch_size": len(batch),
                "entity_ids": sorted([x for x in entity_ids if x]),
                "ok": batch_ok,
                "error": error_text,
                "response": raw_response,
            }
        )

    write_jsonl(run_root / "pass-b.raw.jsonl", rows)

    total_batches = successful + failed
    success_ratio = (successful / total_batches) if total_batches > 0 else 0.0
    accepted, rejected = validate_pass_b_proposals(
        proposals=proposed_raw,
        existing_categories=categories,
        pass_a_decisions=pass_a_decisions,
        enable_title_regex=enable_title_regex,
    )

    status = "ok"
    apply_blocked = False
    apply_block_reason = ""
    if total_batches > 0 and success_ratio == 0.0:
        status = "partial_failure"
        apply_blocked = True
        apply_block_reason = "pass-b failed for all batches"
        accepted = []
    elif (
        total_batches > 0 and success_ratio < THRESHOLDS.pass_b_min_batch_success_ratio
    ):
        status = "partial_failure"
        apply_blocked = True
        apply_block_reason = "pass-b success ratio below threshold"
        accepted = []

    return PassBResult(
        status=status,
        proposals=accepted,
        rejected=rejected,
        left_unassigned_entity_ids=sorted(left_unassigned),
        total_batches=total_batches,
        successful_batches=successful,
        failed_batches=failed,
        success_ratio=round(success_ratio, 4),
        apply_blocked=apply_blocked,
        apply_block_reason=apply_block_reason,
    )
