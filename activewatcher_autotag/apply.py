from __future__ import annotations

import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .merge_rules import validate_categories_payload
from .runtime import file_sha256, read_json, write_json


def _load_review_gate(run_root: Path) -> dict[str, Any]:
    path = run_root / "review-gate.json"
    if path.is_file():
        payload = read_json(path)
        if not isinstance(payload, dict):
            raise ValueError("invalid review-gate.json payload")
        return payload

    template_path = run_root / "review-gate.template.json"
    if not template_path.is_file():
        raise ValueError("missing review gate file: review-gate.json")
    payload = read_json(template_path)
    if not isinstance(payload, dict):
        raise ValueError("invalid review-gate.template.json payload")
    write_json(path, payload)
    return payload


def _require_review_gate(run_root: Path, generated_sha: str) -> dict[str, Any]:
    payload = _load_review_gate(run_root)
    required = [
        "run_id",
        "approved",
        "approved_by",
        "approved_at",
        "categories_generated_sha256",
    ]
    for key in required:
        if key not in payload:
            raise ValueError(f"review gate missing field: {key}")
    if str(payload.get("run_id") or "") != run_root.name:
        raise ValueError("review gate run_id does not match run")
    if bool(payload.get("approved")) is not True:
        raise ValueError("review gate not approved")
    if str(payload.get("categories_generated_sha256") or "") != generated_sha:
        raise ValueError("review gate hash mismatch")
    return payload


def _require_evaluation(run_root: Path, generated_sha: str) -> dict[str, Any]:
    path = run_root / "evaluation.json"
    if not path.is_file():
        raise ValueError("missing evaluation artifact")
    payload = read_json(path)
    if not isinstance(payload, dict):
        raise ValueError("invalid evaluation artifact")
    if str(payload.get("run_id") or "") != run_root.name:
        raise ValueError("evaluation run_id mismatch")
    if str(payload.get("categories_generated_sha256") or "") != generated_sha:
        raise ValueError("evaluation categories hash mismatch")
    gates_raw = payload.get("gates")
    gates: dict[str, Any] = gates_raw if isinstance(gates_raw, dict) else {}
    if not all(bool(v) for v in gates.values()):
        raise ValueError("evaluation gates failed; apply is blocked")
    return payload


def run_apply(*, run_root: Path, categories_path: Path) -> dict[str, Any]:
    generated_path = run_root / "categories.generated.json"
    if not generated_path.is_file():
        raise FileNotFoundError("categories.generated.json not found")
    generated_payload = read_json(generated_path)
    if not isinstance(generated_payload, dict):
        raise ValueError("invalid categories.generated.json payload")
    validate_categories_payload(generated_payload)
    generated_sha = file_sha256(generated_path)

    _require_review_gate(run_root, generated_sha)
    _require_evaluation(run_root, generated_sha)

    target = Path(categories_path).expanduser()
    target.parent.mkdir(parents=True, exist_ok=True)

    temp_path = target.with_name(f"{target.name}.tmp.{os.getpid()}")
    write_json(temp_path, generated_payload)
    temp_payload = read_json(temp_path)
    if not isinstance(temp_payload, dict):
        raise ValueError("temporary categories payload is invalid")
    validate_categories_payload(temp_payload)

    backup_path: Path | None = None
    if target.exists():
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = target.with_name(f"{target.name}.bak.{stamp}")
        shutil.copy2(target, backup_path)

    os.replace(temp_path, target)

    return {
        "run_id": run_root.name,
        "target": str(target),
        "backup": str(backup_path) if backup_path else None,
        "categories_generated_sha256": generated_sha,
        "restart_required": True,
    }
