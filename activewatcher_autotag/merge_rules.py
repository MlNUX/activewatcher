from __future__ import annotations

import colorsys
import re
from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from typing import Any

from activewatcher.common.categories import category_catalog

from .runtime import read_json
from .scanner import normalize_domain

TOKEN_FIELDS = ("apps", "domains", "titles", "urls", "title_regex")
FIELD_LIMITS = {
    "apps": 200,
    "domains": 200,
    "titles": 200,
    "urls": 200,
    "title_regex": 50,
}
_GENERIC_STOP = {
    "app",
    "apps",
    "website",
    "web",
    "home",
    "dashboard",
    "docs",
    "documentation",
    "tab",
    "tabs",
    "new tab",
    "untitled",
}
_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,31}$")


def _empty_tokens() -> dict[str, list[str]]:
    return {field: [] for field in TOKEN_FIELDS}


def _normalize_token(field: str, value: str) -> str:
    raw = str(value or "").strip()
    if not raw:
        return ""
    if field == "title_regex":
        return raw
    token = raw.lower().strip()
    if field == "domains":
        token = normalize_domain(token)
    elif field == "urls":
        token = token.split("?", 1)[0].split("#", 1)[0]
    return token


def sanitize_tokens(
    token_map: dict[str, Any] | None,
    *,
    enable_title_regex: bool,
) -> dict[str, list[str]]:
    src = token_map or {}
    out: dict[str, list[str]] = {}
    for field in TOKEN_FIELDS:
        values = src.get(field)
        if not isinstance(values, list):
            values = []
        seen: set[str] = set()
        cleaned: list[str] = []
        for v in values:
            tok = _normalize_token(field, str(v or ""))
            if not tok:
                continue
            if field != "title_regex" and tok in _GENERIC_STOP:
                continue
            if field == "title_regex" and not enable_title_regex:
                continue
            if tok in seen:
                continue
            seen.add(tok)
            cleaned.append(tok)
            if len(cleaned) >= FIELD_LIMITS[field]:
                break
        out[field] = cleaned
    if not enable_title_regex:
        out["title_regex"] = []
    return out


def category_tokens(category: dict[str, Any]) -> set[str]:
    all_tokens: set[str] = set()
    for field in TOKEN_FIELDS:
        values = category.get(field)
        if not isinstance(values, list):
            continue
        for v in values:
            token = _normalize_token(field, str(v or ""))
            if not token:
                continue
            token = token.lower().strip()
            if token in _GENERIC_STOP:
                continue
            all_tokens.add(token)
    return all_tokens


def _catalog_default_categories() -> list[dict[str, Any]]:
    rules = category_catalog().rules
    out: list[dict[str, Any]] = []
    for r in rules:
        out.append(
            {
                "id": r.id,
                "label": r.label,
                "color": r.color,
                "apps": list(r.apps),
                "domains": list(r.domains),
                "titles": list(r.titles),
                "urls": list(r.urls),
                "title_regex": [rx.pattern for rx in r.title_regex],
            }
        )
    return out


def _sanitize_category(
    item: dict[str, Any],
    *,
    enable_title_regex: bool,
) -> dict[str, Any] | None:
    cat_id = str(item.get("id") or "").strip().lower()
    if not cat_id:
        return None
    label = str(item.get("label") or cat_id).strip() or cat_id
    color = (
        str(item.get("color") or "rgba(255,255,255,.45)").strip()
        or "rgba(255,255,255,.45)"
    )
    tokens = sanitize_tokens(item, enable_title_regex=enable_title_regex)
    return {
        "id": cat_id,
        "label": label,
        "color": color,
        **tokens,
    }


def _ensure_other_last(categories: list[dict[str, Any]]) -> list[dict[str, Any]]:
    out = [c for c in categories if c.get("id") != "other"]
    other = next((c for c in categories if c.get("id") == "other"), None)
    if other is None:
        other = {
            "id": "other",
            "label": "Other",
            "color": "rgba(255,255,255,.45)",
            **_empty_tokens(),
        }
    out.append(other)
    return out


def load_categories(
    path: Path,
    *,
    enable_title_regex: bool,
) -> list[dict[str, Any]]:
    raw_items: list[dict[str, Any]]
    if path.exists() and path.is_file():
        payload = read_json(path)
        if not isinstance(payload, dict) or not isinstance(
            payload.get("categories"), list
        ):
            raise ValueError(f"invalid categories payload: {path}")
        raw_items = [x for x in payload.get("categories", []) if isinstance(x, dict)]
    else:
        raw_items = _catalog_default_categories()

    cleaned: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in raw_items:
        category = _sanitize_category(item, enable_title_regex=enable_title_regex)
        if category is None:
            continue
        cat_id = str(category["id"])
        if cat_id in seen:
            continue
        seen.add(cat_id)
        cleaned.append(category)
    return _ensure_other_last(cleaned)


def _merge_token_lists(
    base: list[str], additions: list[str], *, limit: int
) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for src in (base, additions):
        for token in src:
            t = str(token or "").strip()
            if not t or t in seen:
                continue
            seen.add(t)
            out.append(t)
            if len(out) >= limit:
                return out
    return out


def _relative_luminance(rgb: tuple[int, int, int]) -> float:
    def _chan(v: int) -> float:
        n = v / 255.0
        if n <= 0.03928:
            return n / 12.92
        return ((n + 0.055) / 1.055) ** 2.4

    r, g, b = rgb
    return 0.2126 * _chan(r) + 0.7152 * _chan(g) + 0.0722 * _chan(b)


def _contrast_ratio(a: tuple[int, int, int], b: tuple[int, int, int]) -> float:
    l1 = _relative_luminance(a)
    l2 = _relative_luminance(b)
    hi = max(l1, l2)
    lo = min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)


def color_from_category_id(category_id: str) -> str:
    digest = sha256(category_id.encode("utf-8")).hexdigest()
    value = int(digest[:12], 16)
    hue = float(value % 360) / 360.0
    sat = 0.62
    light = 0.50
    bg = (15, 23, 42)
    for _ in range(8):
        r_f, g_f, b_f = colorsys.hls_to_rgb(hue, light, sat)
        rgb = (int(round(r_f * 255)), int(round(g_f * 255)), int(round(b_f * 255)))
        if _contrast_ratio(rgb, bg) >= 3.0:
            return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"
        light = min(0.75, light + 0.04)
    r_f, g_f, b_f = colorsys.hls_to_rgb(hue, 0.66, sat)
    rgb = (int(round(r_f * 255)), int(round(g_f * 255)), int(round(b_f * 255)))
    return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"


def _next_free_id(existing_ids: set[str], base_id: str) -> str:
    if base_id not in existing_ids:
        return base_id
    n = 2
    while True:
        candidate = f"{base_id}_{n}"
        if candidate not in existing_ids:
            return candidate
        n += 1


def validate_categories_payload(payload: dict[str, Any]) -> None:
    cats = payload.get("categories")
    if not isinstance(cats, list) or not cats:
        raise ValueError("categories payload is empty")
    seen: set[str] = set()
    for idx, cat in enumerate(cats):
        if not isinstance(cat, dict):
            raise ValueError(f"invalid category at index {idx}")
        cat_id = str(cat.get("id") or "").strip().lower()
        if not cat_id:
            raise ValueError(f"missing category id at index {idx}")
        if cat_id in seen:
            raise ValueError(f"duplicate category id: {cat_id}")
        seen.add(cat_id)
    if cats[-1].get("id") != "other":
        raise ValueError("categories payload must end with 'other'")


def merge_category_rules(
    *,
    existing_categories: list[dict[str, Any]],
    pass_a_decisions: list[dict[str, Any]],
    proposals: list[dict[str, Any]],
    enable_title_regex: bool,
    prune: bool,
) -> tuple[dict[str, Any], dict[str, Any]]:
    categories = deepcopy(existing_categories)
    by_id: dict[str, dict[str, Any]] = {str(c["id"]): c for c in categories}

    suggestion_buckets: dict[str, dict[str, list[str]]] = {}
    for decision in pass_a_decisions:
        if str(decision.get("state") or "") != "accepted_existing":
            continue
        target_id = str(decision.get("target_category_id") or "").strip().lower()
        if target_id not in by_id:
            continue
        suggestions = decision.get("token_suggestions")
        if not isinstance(suggestions, dict):
            continue
        sanitized = sanitize_tokens(suggestions, enable_title_regex=enable_title_regex)
        bucket = suggestion_buckets.setdefault(target_id, _empty_tokens())
        for field in TOKEN_FIELDS:
            bucket[field].extend(sanitized.get(field, []))

    for cat in categories:
        cat_id = str(cat["id"])
        existing_tokens = sanitize_tokens(cat, enable_title_regex=enable_title_regex)
        additions = sanitize_tokens(
            suggestion_buckets.get(cat_id, {}), enable_title_regex=enable_title_regex
        )
        for field in TOKEN_FIELDS:
            if prune:
                cat[field] = additions[field][: FIELD_LIMITS[field]]
            else:
                cat[field] = _merge_token_lists(
                    existing_tokens[field], additions[field], limit=FIELD_LIMITS[field]
                )

    existing_ids = {str(c["id"]) for c in categories}
    appended: list[str] = []
    for proposal in proposals:
        base_id = str(proposal.get("id") or "").strip().lower()
        if not _ID_RE.fullmatch(base_id) or base_id == "other":
            continue
        final_id = _next_free_id(existing_ids, base_id)
        existing_ids.add(final_id)
        label = str(proposal.get("label") or final_id).strip() or final_id
        rule_tokens = sanitize_tokens(
            proposal.get("rule_tokens"), enable_title_regex=enable_title_regex
        )
        new_cat = {
            "id": final_id,
            "label": label,
            "color": color_from_category_id(final_id),
            **rule_tokens,
        }
        categories.append(new_cat)
        appended.append(final_id)

    categories = _ensure_other_last(categories)
    payload = {"categories": categories}
    validate_categories_payload(payload)
    stats = {
        "existing_categories": len(existing_categories),
        "final_categories": len(categories),
        "appended_category_ids": appended,
    }
    return payload, stats
