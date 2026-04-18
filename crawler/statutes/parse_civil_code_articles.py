#!/usr/bin/env python3
"""Parse article pages into article-level structured JSONL rows."""

from __future__ import annotations

import argparse
import json
import re
from html import unescape
from pathlib import Path
from typing import Any

FETCH_LOG_PATH = Path("data/parsed/statutes/civil_code/articles/article_fetch_log.jsonl")
ARTICLE_INDEX_PATH = Path("data/parsed/statutes/civil_code/index/article_index.jsonl")
OUTPUT_JSONL_PATH = Path("data/parsed/statutes/civil_code/articles/articles_structured.jsonl")
REPORT_PATH = Path("data/parsed/statutes/civil_code/articles/article_parse_report.json")


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file_obj:
        for raw in file_obj:
            raw = raw.strip()
            if not raw:
                continue
            rows.append(json.loads(raw))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_obj:
        for row in rows:
            file_obj.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize_text(text: str) -> str:
    text = unescape(text.replace("\u00a0", " ").replace("\u3000", " "))
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def html_to_lines(html: str) -> list[str]:
    html = re.sub(r"<script[\\s\\S]*?</script>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<style[\\s\\S]*?</style>", " ", html, flags=re.IGNORECASE)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"</p>|</div>|</tr>|</li>", "\n", html, flags=re.IGNORECASE)
    html = re.sub(r"<[^>]+>", " ", html)
    text = unescape(html)
    raw_lines = [normalize_text(line) for line in text.splitlines()]
    return [line for line in raw_lines if line]


def extract_article_number_and_heading(lines: list[str]) -> tuple[str, str, int]:
    for idx, line in enumerate(lines):
        match = re.search(r"(?:art(?:igo)?\.?\s*)(\d+[.ºo]?)\s*[-—:]?\s*(.*)$", line, flags=re.IGNORECASE)
        if match:
            number = normalize_text(match.group(1))
            heading = normalize_text(match.group(2))
            return number, heading, idx
    return "", "", -1


def build_article_text(lines: list[str], start_index: int) -> str:
    if not lines:
        return ""
    body = lines[start_index + 1 :] if start_index >= 0 else lines
    return "\n".join(body).strip()


def build_index_lookup(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for row in rows:
        url = str(row.get("article_url", "")).strip()
        if url and url not in lookup:
            lookup[url] = row
    return lookup


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse Civil Code article pages.")
    parser.add_argument("--fetch-log-path", type=Path, default=FETCH_LOG_PATH)
    parser.add_argument("--article-index-path", type=Path, default=ARTICLE_INDEX_PATH)
    parser.add_argument("--output-path", type=Path, default=OUTPUT_JSONL_PATH)
    parser.add_argument("--report-path", type=Path, default=REPORT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    fetch_rows = load_jsonl(args.fetch_log_path)
    index_lookup = build_index_lookup(load_jsonl(args.article_index_path))

    output_rows: list[dict[str, Any]] = []
    for row in fetch_rows:
        if row.get("status") != "ok":
            continue

        source_url = str(row.get("source_url", "")).strip()
        html_path = Path(str(row.get("html_path", "")).strip())
        if not html_path.exists():
            continue

        html = html_path.read_text(encoding="utf-8", errors="replace")
        lines = html_to_lines(html)
        number, heading, start_idx = extract_article_number_and_heading(lines)
        article_text = build_article_text(lines, start_idx)

        index_row = index_lookup.get(source_url, {})
        if not number:
            number = normalize_text(str(index_row.get("article_number", "")))
        if not heading:
            label = normalize_text(str(index_row.get("article_label", "")))
            heading = label

        canonical_id = f"mo-civil-code:{number or 'unknown'}"
        needs_review = not bool(number and article_text)

        output_rows.append(
            {
                "code_id": "mo-civil-code",
                "code_name_zh": "澳門民法典",
                "article_canonical_id": canonical_id,
                "article_number": number,
                "article_heading": heading,
                "hierarchy_path": str(index_row.get("hierarchy_path", "")),
                "article_text": article_text,
                "language": "pt",
                "source_url": source_url,
                "parse_method": "deterministic_regex_plus_index_alignment",
                "confidence": 0.86 if not needs_review else 0.55,
                "needs_review": needs_review,
                "source_html_path": str(html_path),
            }
        )

    write_jsonl(args.output_path, output_rows)

    report = {
        "fetch_log_path": str(args.fetch_log_path),
        "article_index_path": str(args.article_index_path),
        "output_path": str(args.output_path),
        "parsed_articles": len(output_rows),
        "needs_review_count": sum(1 for row in output_rows if row["needs_review"]),
    }
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
