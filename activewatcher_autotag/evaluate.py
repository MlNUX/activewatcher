from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import re
from typing import Any

from activewatcher.common.time import parse_rfc3339, to_utc
from activewatcher.server import reports

from .llm_client import validate_local_base_url
from .merge_rules import load_categories, validate_categories_payload
from .runtime import (
    file_sha256,
    goldset_path,
    read_json,
    read_jsonl,
    write_json,
)
from .scanner import connect_readonly, normalize_domain
from .settings import RUNTIME_DEFAULTS, THRESHOLDS


@dataclass(frozen=True)
class EvalRule:
    id: str
    apps: tuple[str, ...]
    domains: tuple[str, ...]
    titles: tuple[str, ...]
    urls: tuple[str, ...]
    title_regex: tuple[re.Pattern[str], ...]


@dataclass(frozen=True)
class EvalCatalog:
    categories: list[EvalRule]
    fallback: str


def _norm_tokens(raw: Any) -> tuple[str, ...]:
    if not isinstance(raw, list):
        return ()
    out: list[str] = []
    seen: set[str] = set()
    for value in raw:
        token = str(value or "").strip().lower()
        if not token or token in seen:
            continue
        seen.add(token)
        out.append(token)
    return tuple(out)


def _compile_regex_tokens(raw: Any) -> tuple[re.Pattern[str], ...]:
    if not isinstance(raw, list):
        return ()
    out: list[re.Pattern[str]] = []
    for value in raw:
        pattern = str(value or "").strip()
        if not pattern:
            continue
        try:
            out.append(re.compile(pattern, re.IGNORECASE))
        except re.error:
            continue
    return tuple(out)


def _build_catalog(categories: list[dict[str, Any]]) -> EvalCatalog:
    rules: list[EvalRule] = []
    for raw in categories:
        if not isinstance(raw, dict):
            continue
        cat_id = str(raw.get("id") or "").strip().lower()
        if not cat_id:
            continue
        rules.append(
            EvalRule(
                id=cat_id,
                apps=_norm_tokens(raw.get("apps")),
                domains=_norm_tokens(raw.get("domains")),
                titles=_norm_tokens(raw.get("titles")),
                urls=_norm_tokens(raw.get("urls")),
                title_regex=_compile_regex_tokens(raw.get("title_regex")),
            )
        )
    fallback = rules[-1].id if rules else "other"
    return EvalCatalog(categories=rules, fallback=fallback)


def _matches_text(value: str, tokens: list[str]) -> bool:
    text = str(value or "").strip().lower()
    if not text:
        return False
    return any(token in text for token in tokens)


def _matches_domain(domain: str, tokens: list[str]) -> bool:
    d = str(domain or "").strip().lower()
    if not d:
        return False
    for token in tokens:
        t = str(token or "").strip().lower()
        if not t:
            continue
        if "." in t:
            if d == t or d.endswith(f".{t}"):
                return True
        elif t in d:
            return True
    return False


def _matches_regex(value: str, patterns: tuple[re.Pattern[str], ...]) -> bool:
    text = str(value or "")
    if not text:
        return False
    return any(pattern.search(text) for pattern in patterns)


def _classify_app(catalog: EvalCatalog, *, app: str, title: str) -> str:
    app_norm = str(app or "").strip().lower()
    title_norm = str(title or "").strip().lower()
    for category in catalog.categories:
        if _matches_text(app_norm, list(category.apps)):
            return category.id
        if _matches_text(title_norm, list(category.titles)):
            return category.id
        if _matches_regex(title, category.title_regex):
            return category.id
    return catalog.fallback


def _classify_tab(catalog: EvalCatalog, *, url: str, title: str, app: str) -> str:
    url_norm = str(url or "").strip().lower()
    title_norm = str(title or "").strip().lower()
    app_norm = str(app or "").strip().lower()
    domain = normalize_domain(url_norm)
    for category in catalog.categories:
        if _matches_text(app_norm, list(category.apps)):
            return category.id
        if _matches_domain(domain, list(category.domains)):
            return category.id
        if _matches_text(title_norm, list(category.titles)):
            return category.id
        if _matches_text(url_norm, list(category.urls)):
            return category.id
        if _matches_regex(title, category.title_regex):
            return category.id
    return catalog.fallback


def _category_totals(
    *,
    conn: sqlite3.Connection,
    from_dt: datetime,
    to_dt: datetime,
    catalog: EvalCatalog,
) -> dict[str, float]:
    totals: dict[str, float] = {}
    _, _, window = reports.load_intervals(
        conn,
        bucket="window",
        source=None,
        from_ts=from_dt,
        to_ts=to_dt,
    )
    for it in window:
        app = str(it.data.get("app") or "")
        if not app or app.startswith("__"):
            continue
        title = str(it.data.get("title") or "")
        cat = _classify_app(catalog, app=app, title=title)
        totals[cat] = totals.get(cat, 0.0) + it.duration_seconds()

    _, _, tabs = reports.load_intervals(
        conn,
        bucket="browser_tabs",
        source=None,
        from_ts=from_dt,
        to_ts=to_dt,
    )
    for it in tabs:
        tabs_data = it.data.get("tabs")
        if not isinstance(tabs_data, list) or not tabs_data:
            continue
        browser = str(it.data.get("browser") or it.source or "")
        dur = it.duration_seconds()
        if dur <= 0:
            continue
        for tab in tabs_data:
            if not isinstance(tab, dict):
                continue
            url = str(
                tab.get("url") or tab.get("pending_url") or tab.get("pendingUrl") or ""
            )
            title = str(tab.get("title") or "")
            cat = _classify_tab(catalog, url=url, title=title, app=browser)
            totals[cat] = totals.get(cat, 0.0) + dur

    return totals


def _weighted_f1(
    expected: list[str], predicted: list[str], weights: list[float]
) -> float:
    labels = sorted(set(expected) | set(predicted))
    total_support = 0.0
    weighted_sum = 0.0
    for label in labels:
        tp = 0.0
        fp = 0.0
        fn = 0.0
        support = 0.0
        for exp, pred, w in zip(expected, predicted, weights):
            if exp == label:
                support += w
            if exp == label and pred == label:
                tp += w
            elif exp != label and pred == label:
                fp += w
            elif exp == label and pred != label:
                fn += w
        precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (
            (2.0 * precision * recall / (precision + recall))
            if (precision + recall) > 0
            else 0.0
        )
        weighted_sum += f1 * support
        total_support += support
    if total_support <= 0:
        return 0.0
    return weighted_sum / total_support


def _predict_goldset(catalog: EvalCatalog, row: dict[str, Any]) -> str:
    entity_type = str(row.get("entity_type") or "")
    entity = str(row.get("entity") or "")
    if entity_type == "app":
        return _classify_app(catalog, app=entity, title="")
    if entity_type == "domain":
        return _classify_tab(catalog, url=f"https://{entity}", title="", app="")
    return catalog.fallback


def _read_review_gate_allowlist(run_root: Path) -> set[str]:
    path = run_root / "review-gate.json"
    if not path.is_file():
        return set()
    try:
        payload = read_json(path)
    except Exception:
        return set()
    if not isinstance(payload, dict):
        return set()
    values = payload.get("allowed_category_drop_ids")
    if not isinstance(values, list):
        return set()
    return {str(v).strip() for v in values if str(v).strip()}


def _flat_taxonomy_ok(categories: list[dict[str, Any]]) -> bool:
    forbidden = ("parent", "parent_id", "children", "child_ids", "subcategories")
    for category in categories:
        if not isinstance(category, dict):
            return False
        for key in forbidden:
            if key not in category:
                continue
            value = category.get(key)
            if value in (None, "", [], {}, False):
                continue
            return False
    return True


def _llm_local_only_ok(metadata: dict[str, Any]) -> bool:
    llm_raw = metadata.get("llm")
    if not isinstance(llm_raw, dict):
        return False
    provider = str(llm_raw.get("provider") or "").strip().lower()
    if provider != "ollama":
        return False
    base_url = str(llm_raw.get("base_url") or "").strip()
    if not base_url:
        return False
    try:
        validate_local_base_url(base_url)
    except Exception:
        return False
    return True


def _new_category_combined_floor_ok(run_root: Path) -> bool:
    decisions_path = run_root / "autotag-decisions.jsonl"
    if not decisions_path.is_file():
        return True
    try:
        rows = read_jsonl(decisions_path)
    except Exception:
        return False

    grouped: dict[str, dict[str, set[str]]] = {}
    for row in rows:
        if str(row.get("decision_type") or "") != "pass_b_member":
            continue
        proposal_id = str(row.get("target_category_id") or "").strip().lower()
        entity_type = str(row.get("entity_type") or "").strip().lower()
        entity = str(row.get("entity") or "").strip().lower()
        if not proposal_id or entity_type not in {"app", "domain"} or not entity:
            continue
        bucket = grouped.setdefault(proposal_id, {"apps": set(), "domains": set()})
        if entity_type == "app":
            bucket["apps"].add(entity)
        else:
            bucket["domains"].add(entity)

    for bucket in grouped.values():
        combined = len(bucket["apps"]) + len(bucket["domains"])
        if combined < THRESHOLDS.new_category_min_combined_entities:
            return False
    return True


def _max_new_categories_ok(pass_b_meta: dict[str, Any]) -> bool:
    accepted = int(pass_b_meta.get("accepted_proposals") or 0)
    return accepted <= THRESHOLDS.max_new_categories


def run_evaluate(
    *, run_root: Path, allow_missing_goldset: bool = False
) -> dict[str, Any]:
    metadata_path = run_root / "run-metadata.json"
    metadata = read_json(metadata_path)
    if not isinstance(metadata, dict):
        raise ValueError("invalid run metadata")

    db_path = Path(str(metadata.get("db_path") or ""))
    categories_path = Path(str(metadata.get("categories_path") or ""))
    from_dt = to_utc(parse_rfc3339(str(metadata.get("from_ts"))))
    to_dt = to_utc(parse_rfc3339(str(metadata.get("to_ts"))))

    baseline_categories = load_categories(
        categories_path,
        enable_title_regex=bool(
            metadata.get("enable_title_regex", RUNTIME_DEFAULTS.enable_title_regex)
        ),
    )
    generated_payload = read_json(run_root / "categories.generated.json")
    if not isinstance(generated_payload, dict):
        raise ValueError("invalid categories.generated.json")
    validate_categories_payload(generated_payload)
    generated_categories = [
        x for x in generated_payload.get("categories", []) if isinstance(x, dict)
    ]

    baseline_catalog = _build_catalog(baseline_categories)
    generated_catalog = _build_catalog(generated_categories)

    conn = connect_readonly(db_path)
    try:
        baseline_totals = _category_totals(
            conn=conn, from_dt=from_dt, to_dt=to_dt, catalog=baseline_catalog
        )
        generated_totals = _category_totals(
            conn=conn, from_dt=from_dt, to_dt=to_dt, catalog=generated_catalog
        )
    finally:
        conn.close()

    baseline_totals = baseline_totals or {}
    generated_totals = generated_totals or {}

    baseline_total_seconds = float(sum(baseline_totals.values()))
    generated_total_seconds = float(sum(generated_totals.values()))
    baseline_other_seconds = float(baseline_totals.get("other", 0.0))
    generated_other_seconds = float(generated_totals.get("other", 0.0))
    baseline_other_share = (
        baseline_other_seconds / baseline_total_seconds
        if baseline_total_seconds > 0
        else 0.0
    )
    generated_other_share = (
        generated_other_seconds / generated_total_seconds
        if generated_total_seconds > 0
        else 0.0
    )

    allowlist = _read_review_gate_allowlist(run_root)
    drop_failures: list[dict[str, Any]] = []
    baseline_existing_ids = [
        str(c.get("id") or "")
        for c in baseline_categories
        if isinstance(c, dict) and str(c.get("id") or "") != "other"
    ]
    for cat_id in baseline_existing_ids:
        base = float(baseline_totals.get(cat_id, 0.0))
        new = float(generated_totals.get(cat_id, 0.0))
        abs_drop = base - new
        rel_drop = (abs_drop / base) if base > 0 else 0.0
        if (
            cat_id not in allowlist
            and abs_drop > THRESHOLDS.category_drop_absolute_fail_threshold_seconds
            and rel_drop > THRESHOLDS.category_drop_relative_fail_threshold
        ):
            drop_failures.append(
                {
                    "category_id": cat_id,
                    "baseline_seconds": round(base, 3),
                    "generated_seconds": round(new, 3),
                    "relative_drop": round(rel_drop, 4),
                    "absolute_drop_seconds": round(abs_drop, 3),
                }
            )

    goldset_file = goldset_path()
    goldset_rows = read_jsonl(goldset_file) if goldset_file.is_file() else []
    goldset_count = len(goldset_rows)
    expected: list[str] = []
    baseline_pred: list[str] = []
    generated_pred: list[str] = []
    weights: list[float] = []
    for row in goldset_rows:
        expected_id = str(row.get("expected_category_id") or "").strip()
        if not expected_id:
            continue
        expected.append(expected_id)
        baseline_pred.append(_predict_goldset(baseline_catalog, row))
        generated_pred.append(_predict_goldset(generated_catalog, row))
        try:
            weights.append(float(row.get("weight") or 1.0))
        except Exception:
            weights.append(1.0)

    baseline_f1 = _weighted_f1(expected, baseline_pred, weights) if expected else 0.0
    generated_f1 = _weighted_f1(expected, generated_pred, weights) if expected else 0.0

    goldset_required = bool(RUNTIME_DEFAULTS.goldset_required_for_apply)
    if allow_missing_goldset:
        goldset_required = False

    suggest_raw = metadata.get("suggest")
    suggest_meta: dict[str, Any] = suggest_raw if isinstance(suggest_raw, dict) else {}
    pass_a_raw = suggest_meta.get("pass_a")
    pass_a_meta: dict[str, Any] = pass_a_raw if isinstance(pass_a_raw, dict) else {}
    pass_b_raw = suggest_meta.get("pass_b")
    pass_b_meta: dict[str, Any] = pass_b_raw if isinstance(pass_b_raw, dict) else {}

    hard_policy_checks = {
        "flat_taxonomy": _flat_taxonomy_ok(generated_categories),
        "llm_local_only": _llm_local_only_ok(metadata),
        "new_category_combined_floor": _new_category_combined_floor_ok(run_root),
        "max_new_categories": _max_new_categories_ok(pass_b_meta),
    }
    hard_policy_ok = all(hard_policy_checks.values())
    schema_valid_gate = (
        int(pass_a_meta.get("failed_batches") or 0) == 0
        and int(pass_b_meta.get("failed_batches") or 0) == 0
    )

    gates = {
        "hard_policy_ok": hard_policy_ok,
        "schema_valid_outputs": schema_valid_gate,
        "other_not_worse": generated_other_seconds <= baseline_other_seconds,
        "category_drop_guard": len(drop_failures) == 0,
        "goldset_exists": (goldset_count > 0) if goldset_required else True,
        "goldset_size_ok": (
            RUNTIME_DEFAULTS.goldset_min_entities
            <= goldset_count
            <= RUNTIME_DEFAULTS.goldset_max_entities
        )
        if goldset_required
        else True,
        "goldset_f1_not_lower": (generated_f1 >= baseline_f1)
        if goldset_required
        else True,
        "pass_b_apply_ok": not bool(pass_b_meta.get("apply_blocked", False)),
    }
    recommend_apply = all(gates.values())

    evaluation = {
        "run_id": run_root.name,
        "from_ts": metadata.get("from_ts"),
        "to_ts": metadata.get("to_ts"),
        "categories_generated_sha256": file_sha256(
            run_root / "categories.generated.json"
        ),
        "metrics": {
            "baseline_total_seconds": round(baseline_total_seconds, 3),
            "generated_total_seconds": round(generated_total_seconds, 3),
            "baseline_other_seconds": round(baseline_other_seconds, 3),
            "generated_other_seconds": round(generated_other_seconds, 3),
            "baseline_other_share": round(baseline_other_share, 4),
            "generated_other_share": round(generated_other_share, 4),
        },
        "drop_failures": drop_failures,
        "goldset": {
            "path": str(goldset_file),
            "entity_count": goldset_count,
            "baseline_weighted_f1": round(baseline_f1, 6),
            "generated_weighted_f1": round(generated_f1, 6),
            "required_for_apply": goldset_required,
            "override_allow_missing_goldset": bool(allow_missing_goldset),
        },
        "hard_policy_checks": hard_policy_checks,
        "gates": gates,
        "recommend_apply": recommend_apply,
    }
    write_json(run_root / "evaluation.json", evaluation)

    report_lines = [
        f"# Autotag Report - {run_root.name}",
        "",
        "## Evaluation",
        f"- baseline other seconds: {baseline_other_seconds:.3f}",
        f"- generated other seconds: {generated_other_seconds:.3f}",
        f"- baseline weighted F1: {baseline_f1:.6f}",
        f"- generated weighted F1: {generated_f1:.6f}",
        f"- drop failures: {len(drop_failures)}",
        f"- goldset required for apply: {'yes' if goldset_required else 'no'}",
        f"- recommend apply: {'yes' if recommend_apply else 'no'}",
        "",
        "## Gates",
    ]
    for key, value in gates.items():
        report_lines.append(f"- {key}: {'pass' if value else 'fail'}")
    report_lines.append("")
    report_lines.append("## Hard Policy Checks")
    for key, value in hard_policy_checks.items():
        report_lines.append(f"- {key}: {'pass' if value else 'fail'}")
    report_lines.append("")
    if drop_failures:
        report_lines.append("## Category Drop Failures")
        for row in drop_failures:
            report_lines.append(
                f"- {row['category_id']}: relative_drop={row['relative_drop']:.4f} absolute_drop_seconds={row['absolute_drop_seconds']:.3f}"
            )
        report_lines.append("")
    (run_root / "autotag-report.md").write_text(
        "\n".join(report_lines), encoding="utf-8"
    )

    metadata["evaluate"] = {
        "gates": gates,
        "hard_policy_checks": hard_policy_checks,
        "goldset_required_for_apply": goldset_required,
        "allow_missing_goldset": bool(allow_missing_goldset),
        "recommend_apply": recommend_apply,
        "baseline_other_seconds": baseline_other_seconds,
        "generated_other_seconds": generated_other_seconds,
        "baseline_weighted_f1": baseline_f1,
        "generated_weighted_f1": generated_f1,
    }
    write_json(metadata_path, metadata)
    return evaluation
