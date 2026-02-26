from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
from typing import Any

from .llm_client import OllamaClient
from .merge_rules import load_categories, merge_category_rules
from .pass_a_classify import run_pass_a
from .pass_b_propose import run_pass_b
from .runtime import (
    file_sha256,
    prompts_dir,
    read_json,
    utc_rfc3339,
    write_json,
    write_jsonl,
)


def _prompt_hashes() -> dict[str, str]:
    out: dict[str, str] = {}
    for name in [
        "pass_a_classify.system.txt",
        "pass_a_classify.user.template.txt",
        "pass_b_propose.system.txt",
        "pass_b_propose.user.template.txt",
    ]:
        path = prompts_dir() / name
        if not path.is_file():
            continue
        out[name] = sha256(path.read_bytes()).hexdigest()
    return out


def _build_review_gate_template(
    *, run_root: Path, categories_generated_sha256: str
) -> dict[str, Any]:
    return {
        "run_id": run_root.name,
        "approved": False,
        "approved_by": "",
        "approved_at": "",
        "categories_generated_sha256": categories_generated_sha256,
        "allowed_category_drop_ids": [],
    }


def _report_markdown(
    *,
    run_id: str,
    pass_a: dict[str, Any],
    pass_b: dict[str, Any],
    merge_stats: dict[str, Any],
    apply_blocked: bool,
    apply_block_reason: str,
) -> str:
    lines = [
        f"# Autotag Report - {run_id}",
        "",
        "## Pass A",
        f"- total decisions: {pass_a['decision_count']}",
        f"- accepted_existing: {pass_a['accepted_existing']}",
        f"- review_existing: {pass_a['review_existing']}",
        f"- unknown_candidate: {pass_a['unknown_candidate']}",
        f"- batches: {pass_a['successful_batches']}/{pass_a['total_batches']} successful",
        "",
        "## Pass B",
        f"- status: {pass_b['status']}",
        f"- proposals accepted: {pass_b['accepted_proposals']}",
        f"- proposals rejected: {pass_b['rejected_proposals']}",
        f"- batches: {pass_b['successful_batches']}/{pass_b['total_batches']} successful",
        f"- success ratio: {pass_b['success_ratio']:.3f}",
        "",
        "## Merge",
        f"- existing categories: {merge_stats['existing_categories']}",
        f"- final categories: {merge_stats['final_categories']}",
        f"- appended category ids: {', '.join(merge_stats.get('appended_category_ids', [])) or '(none)'}",
        "",
        "## Apply Recommendation",
        f"- apply_blocked: {'yes' if apply_blocked else 'no'}",
        f"- reason: {apply_block_reason or 'none'}",
        "",
    ]
    return "\n".join(lines)


def run_suggest(
    *,
    run_root: Path,
    categories_path: Path,
    provider: str,
    model: str,
    ollama_base_url: str,
    temperature: float,
    top_p: float,
    timeout_seconds: int,
    max_retries: int,
    batch_size: int,
    enable_title_regex: bool,
    prune: bool,
) -> dict[str, Any]:
    if provider.strip().lower() != "ollama":
        raise ValueError("v1 only supports provider=ollama")

    metadata_path = run_root / "run-metadata.json"
    metadata = read_json(metadata_path)
    if not isinstance(metadata, dict):
        metadata = {}

    llm = OllamaClient(base_url=ollama_base_url)
    existing_categories = load_categories(
        categories_path, enable_title_regex=enable_title_regex
    )

    pass_a_result = run_pass_a(
        run_root=run_root,
        categories=existing_categories,
        llm_client=llm,
        model=model,
        temperature=temperature,
        top_p=top_p,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        batch_size=batch_size,
        enable_title_regex=enable_title_regex,
    )

    pass_b_result = run_pass_b(
        run_root=run_root,
        unknown_pool=pass_a_result.unknown_pool,
        categories=existing_categories,
        pass_a_decisions=pass_a_result.decisions,
        llm_client=llm,
        model=model,
        temperature=temperature,
        top_p=top_p,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
        batch_size=batch_size,
        enable_title_regex=enable_title_regex,
    )

    generated_payload, merge_stats = merge_category_rules(
        existing_categories=existing_categories,
        pass_a_decisions=pass_a_result.decisions,
        proposals=pass_b_result.proposals,
        enable_title_regex=enable_title_regex,
        prune=prune,
    )
    generated_path = run_root / "categories.generated.json"
    write_json(generated_path, generated_payload)
    generated_sha = file_sha256(generated_path)

    prompt_hashes = _prompt_hashes()
    decision_logs: list[dict[str, Any]] = []
    for row in pass_a_result.decisions:
        decision_logs.append(
            {
                "run_id": run_root.name,
                "decision_type": "pass_a",
                "entity_id": row.get("entity_id"),
                "entity_type": row.get("entity_type"),
                "entity": row.get("entity"),
                "state": row.get("state"),
                "target_category_id": row.get("target_category_id"),
                "confidence": row.get("confidence"),
                "reasons": row.get("reasons", []),
                "risk_flags": row.get("risk_flags", []),
                "token_suggestions": row.get("token_suggestions", {}),
                "schema_version": "autotag.classify.v1",
                "prompt_version": prompt_hashes.get("pass_a_classify.system.txt", ""),
                "created_at": utc_rfc3339(datetime.now(timezone.utc)),
            }
        )

    for proposal in pass_b_result.proposals:
        for member in proposal.get("members", []):
            if not isinstance(member, dict):
                continue
            decision_logs.append(
                {
                    "run_id": run_root.name,
                    "decision_type": "pass_b_member",
                    "entity_id": member.get("entity_id"),
                    "entity_type": member.get("entity_type"),
                    "entity": member.get("entity"),
                    "state": "proposed_new_category",
                    "target_category_id": proposal.get("id"),
                    "confidence": member.get("confidence"),
                    "reasons": [proposal.get("description")],
                    "risk_flags": [],
                    "schema_version": "autotag.propose.v1",
                    "prompt_version": prompt_hashes.get(
                        "pass_b_propose.system.txt", ""
                    ),
                    "created_at": utc_rfc3339(datetime.now(timezone.utc)),
                }
            )

    write_jsonl(run_root / "autotag-decisions.jsonl", decision_logs)

    review_template = _build_review_gate_template(
        run_root=run_root, categories_generated_sha256=generated_sha
    )
    write_json(run_root / "review-gate.template.json", review_template)
    review_gate_path = run_root / "review-gate.json"
    if not review_gate_path.is_file():
        write_json(review_gate_path, review_template)

    pass_a_summary = {
        "decision_count": len(pass_a_result.decisions),
        "accepted_existing": sum(
            1 for x in pass_a_result.decisions if x.get("state") == "accepted_existing"
        ),
        "review_existing": sum(
            1 for x in pass_a_result.decisions if x.get("state") == "review_existing"
        ),
        "unknown_candidate": sum(
            1 for x in pass_a_result.decisions if x.get("state") == "unknown_candidate"
        ),
        "total_batches": pass_a_result.total_batches,
        "successful_batches": pass_a_result.successful_batches,
        "failed_batches": pass_a_result.failed_batches,
    }
    pass_b_summary = {
        "status": pass_b_result.status,
        "accepted_proposals": len(pass_b_result.proposals),
        "rejected_proposals": len(pass_b_result.rejected),
        "left_unassigned_count": len(pass_b_result.left_unassigned_entity_ids),
        "total_batches": pass_b_result.total_batches,
        "successful_batches": pass_b_result.successful_batches,
        "failed_batches": pass_b_result.failed_batches,
        "success_ratio": pass_b_result.success_ratio,
        "apply_blocked": pass_b_result.apply_blocked,
        "apply_block_reason": pass_b_result.apply_block_reason,
    }

    apply_blocked = bool(pass_b_result.apply_blocked)
    apply_block_reason = str(pass_b_result.apply_block_reason or "")
    report = _report_markdown(
        run_id=run_root.name,
        pass_a=pass_a_summary,
        pass_b=pass_b_summary,
        merge_stats=merge_stats,
        apply_blocked=apply_blocked,
        apply_block_reason=apply_block_reason,
    )
    (run_root / "autotag-report.md").write_text(report, encoding="utf-8")

    metadata["llm"] = {
        "provider": provider,
        "model": model,
        "temperature": temperature,
        "top_p": top_p,
        "timeout_seconds": timeout_seconds,
        "max_retries": max_retries,
        "batch_size": batch_size,
        "base_url": ollama_base_url,
    }
    metadata["enable_title_regex"] = bool(enable_title_regex)
    metadata["prompt_hashes"] = prompt_hashes
    metadata["suggest"] = {
        "pass_a": pass_a_summary,
        "pass_b": pass_b_summary,
        "merge": merge_stats,
        "apply_blocked": apply_blocked,
        "apply_block_reason": apply_block_reason,
        "categories_generated_sha256": generated_sha,
    }
    write_json(metadata_path, metadata)

    return {
        "run_id": run_root.name,
        "categories_generated_path": str(generated_path),
        "categories_generated_sha256": generated_sha,
        "pass_a": pass_a_summary,
        "pass_b": pass_b_summary,
        "merge": merge_stats,
        "apply_blocked": apply_blocked,
        "apply_block_reason": apply_block_reason,
    }
