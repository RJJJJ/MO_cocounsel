"""Shared success heuristic for court text detail extraction runs."""

from __future__ import annotations


def compute_extraction_success(
    attempted: int,
    successful: int,
    failed: int,
    non_empty_full_text_count: int,
    *,
    min_successful: int = 1,
    max_failure_ratio: float = 0.5,
) -> tuple[bool, float]:
    """Return (appears_successful, failure_ratio).

    Heuristic principles:
    - success is driven by recovered non-empty full_text, not navigation counters
    - at least one validated extraction must exist
    - failure ratio should stay within an acceptable bound
    """

    attempted_safe = max(0, attempted)
    failed_safe = max(0, failed)
    failure_ratio = (failed_safe / attempted_safe) if attempted_safe else 1.0

    has_valid_text = non_empty_full_text_count >= min_successful
    has_success = successful >= min_successful
    acceptable_failure_ratio = failure_ratio <= max_failure_ratio

    appears_successful = has_valid_text and has_success and acceptable_failure_ratio
    return appears_successful, failure_ratio
