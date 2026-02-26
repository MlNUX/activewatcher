from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Thresholds:
    classify_auto_accept_min_confidence: float = 0.78
    classify_review_min_confidence: float = 0.60
    unknown_pool_review_cutoff: float = 0.70
    new_category_min_combined_entities: int = 10
    new_category_min_avg_member_confidence: float = 0.74
    new_category_min_cohesion_score: float = 0.70
    new_category_min_total_seconds: float = 7200.0
    new_category_min_active_days: int = 3
    subcategory_similarity_block_threshold: float = 0.82
    subcategory_containment_block_threshold: float = 0.70
    subcategory_containment_hard_block_threshold: float = 0.85
    max_new_categories: int = 4
    pass_b_min_batch_success_ratio: float = 0.80
    category_drop_relative_fail_threshold: float = 0.20
    category_drop_absolute_fail_threshold_seconds: float = 1800.0
    active_day_min_seconds: float = 300.0


@dataclass(frozen=True)
class LlmDefaults:
    provider: str = "ollama"
    model: str = "qwen2.5:14b"
    temperature: float = 0.10
    top_p: float = 0.90
    timeout_seconds: int = 120
    max_retries: int = 2
    batch_size: int = 64


@dataclass(frozen=True)
class RuntimeDefaults:
    artifact_retention_days: int = 30
    default_from_window: str = "90d"
    default_to_window: str = "now"
    default_timezone: str = "UTC"
    lock_stale_after_minutes: int = 30
    enable_title_regex: bool = False
    goldset_required_for_apply: bool = True
    goldset_min_entities: int = 150
    goldset_max_entities: int = 300


THRESHOLDS = Thresholds()
LLM_DEFAULTS = LlmDefaults()
RUNTIME_DEFAULTS = RuntimeDefaults()
