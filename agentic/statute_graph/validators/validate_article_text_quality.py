"""Deterministic text quality validators for parsed Civil Code articles."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from agentic.statute_graph.schemas import ValidatorIssue

HEADER_PREFIX_RE = re.compile(r"^(澳門民法典|c[óo]digo\s+civil|boletim\s+oficial)", flags=re.IGNORECASE)
NOISE_HEADING_RE = re.compile(r"^(home|índice|indice|lista|navigation|menu)", flags=re.IGNORECASE)


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


def validate_article_text_quality(article_jsonl_path: Path) -> list[ValidatorIssue]:
    rows = _load_jsonl(article_jsonl_path)
    issues: list[ValidatorIssue] = []

    for idx, row in enumerate(rows, start=1):
        article_text = str(row.get("article_text", "")).strip()
        heading = str(row.get("article_heading", "")).strip()

        if not article_text:
            issues.append(
                ValidatorIssue(
                    issue_code="article_text_empty",
                    severity="critical",
                    description="Article text is empty.",
                    evidence={"row_index": idx, "article_number": row.get("article_number", "")},
                    suggested_target_file="crawler/statutes/parse_civil_code_articles.py",
                    suggested_target_function="build_article_text",
                )
            )
            continue

        first_line = article_text.splitlines()[0].strip()
        if HEADER_PREFIX_RE.search(first_line):
            issues.append(
                ValidatorIssue(
                    issue_code="article_text_header_prefix",
                    severity="medium",
                    description="Article text begins with title/header-like prefix.",
                    evidence={"row_index": idx, "first_line": first_line[:160]},
                    suggested_target_file="crawler/statutes/parse_civil_code_articles.py",
                    suggested_target_function="html_to_lines",
                )
            )

        heading_lc = heading.lower()
        if not heading or NOISE_HEADING_RE.search(heading_lc) or len(heading) > 180:
            issues.append(
                ValidatorIssue(
                    issue_code="article_heading_suspected_noise",
                    severity="medium",
                    description="Article heading appears to be page title/UI noise.",
                    evidence={"row_index": idx, "article_heading": heading[:200]},
                    suggested_target_file="crawler/statutes/parse_civil_code_articles.py",
                    suggested_target_function="extract_article_number_and_heading",
                )
            )

    return issues
