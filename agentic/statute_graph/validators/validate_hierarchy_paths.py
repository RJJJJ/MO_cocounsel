"""Deterministic validation for hierarchy path pollution patterns."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from agentic.statute_graph.schemas import ValidatorIssue

ARTICLE_TOKEN_RE = re.compile(r"第\s*\d+\s*條")


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


def validate_hierarchy_paths(article_jsonl_path: Path) -> list[ValidatorIssue]:
    rows = _load_jsonl(article_jsonl_path)
    issues: list[ValidatorIssue] = []

    for idx, row in enumerate(rows, start=1):
        hierarchy_path = str(row.get("hierarchy_path", "")).strip()
        if not hierarchy_path:
            continue
        article_tokens = ARTICLE_TOKEN_RE.findall(hierarchy_path)
        if len(article_tokens) > 1:
            issues.append(
                ValidatorIssue(
                    issue_code="nested_article_hierarchy_path",
                    severity="high",
                    description="Hierarchy path contains nested article tokens (article-under-article).",
                    evidence={
                        "row_index": idx,
                        "hierarchy_path": hierarchy_path,
                        "article_tokens": article_tokens,
                        "source_url": row.get("source_url", ""),
                    },
                    suggested_target_file="crawler/statutes/build_civil_code_hierarchy.py",
                    suggested_target_function="build_path",
                )
            )

    return issues
