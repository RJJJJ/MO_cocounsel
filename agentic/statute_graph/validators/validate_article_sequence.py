"""Deterministic article-number sequence validation."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from agentic.statute_graph.schemas import ValidatorIssue


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as file_obj:
        for raw in file_obj:
            raw = raw.strip()
            if raw:
                rows.append(json.loads(raw))
    return rows


def _parse_number(value: str) -> int | None:
    cleaned = value.strip()
    if not cleaned:
        return None
    match = re.search(r"(\d+)", cleaned)
    if not match:
        return None
    return int(match.group(1))


def validate_article_sequence(article_jsonl_path: Path) -> list[ValidatorIssue]:
    rows = _load_jsonl(article_jsonl_path)
    issues: list[ValidatorIssue] = []

    seen: dict[int, int] = {}
    ordered_numbers: list[int] = []

    for idx, row in enumerate(rows, start=1):
        raw_number = str(row.get("article_number", "")).strip()
        parsed = _parse_number(raw_number)

        if parsed is None:
            issues.append(
                ValidatorIssue(
                    issue_code="article_number_missing",
                    severity="high",
                    description="Article number is empty or unparsable.",
                    evidence={"row_index": idx, "article_number": raw_number, "source_url": row.get("source_url", "")},
                    suggested_target_file="crawler/statutes/parse_civil_code_articles.py",
                    suggested_target_function="extract_article_number_and_heading",
                )
            )
            continue

        ordered_numbers.append(parsed)
        seen[parsed] = seen.get(parsed, 0) + 1

    duplicates = sorted(number for number, count in seen.items() if count > 1)
    for duplicate in duplicates:
        issues.append(
            ValidatorIssue(
                issue_code="article_number_duplicate",
                severity="critical",
                description="Detected duplicate article number.",
                evidence={"article_number": duplicate, "count": seen[duplicate]},
                suggested_target_file="crawler/statutes/build_civil_code_hierarchy.py",
                suggested_target_function="extract_article_number",
            )
        )

    if ordered_numbers:
        min_number = min(ordered_numbers)
        max_number = max(ordered_numbers)
        expected = set(range(min_number, max_number + 1))
        missing = sorted(expected - set(ordered_numbers))
        if missing:
            issues.append(
                ValidatorIssue(
                    issue_code="article_number_gap_detected",
                    severity="medium",
                    description="Detected gaps in sequential article numbers.",
                    evidence={"min": min_number, "max": max_number, "missing_numbers": missing[:30]},
                    suggested_target_file="crawler/statutes/classify_civil_code_index_lines_with_ollama.py",
                    suggested_target_function="heuristic_classification",
                )
            )

    return issues
