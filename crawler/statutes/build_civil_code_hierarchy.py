#!/usr/bin/env python3
"""Build deterministic Civil Code hierarchy from line-level classified records."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

INPUT_PATH = Path("data/parsed/statutes/civil_code/index/index_lines_classified.jsonl")
NODES_OUTPUT_PATH = Path("data/parsed/statutes/civil_code/index/hierarchy_nodes.jsonl")
ARTICLE_INDEX_OUTPUT_PATH = Path("data/parsed/statutes/civil_code/index/article_index.jsonl")
REPORT_PATH = Path("data/parsed/statutes/civil_code/index/hierarchy_build_report.json")


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


def slugify(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9\u4e00-\u9fff]+", "-", text.strip().lower())
    cleaned = re.sub(r"-+", "-", cleaned).strip("-")
    return cleaned or "untitled"


def extract_article_number(text: str) -> str:
    match = re.search(r"(?:art(?:igo)?\.?\s*)(\d+[.ºo]?)", text, flags=re.IGNORECASE)
    if match:
        return match.group(1)
    return ""


def build_path(stack: list[dict[str, str]], leaf_label: str) -> str:
    parts = [item["label"] for item in stack if item.get("label")]
    parts.append(leaf_label)
    return " / ".join(parts)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Civil Code hierarchy from classified lines.")
    parser.add_argument("--input-path", type=Path, default=INPUT_PATH)
    parser.add_argument("--nodes-output-path", type=Path, default=NODES_OUTPUT_PATH)
    parser.add_argument("--article-index-output-path", type=Path, default=ARTICLE_INDEX_OUTPUT_PATH)
    parser.add_argument("--report-path", type=Path, default=REPORT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = load_jsonl(args.input_path)

    stack: list[dict[str, str]] = []
    type_rank = {"part": 1, "chapter": 2, "section": 3}

    nodes: list[dict[str, Any]] = []
    article_rows: list[dict[str, Any]] = []

    for order_index, row in enumerate(rows, start=1):
        node_type = str(row.get("node_type", "noise"))
        label = str(row.get("repaired_line") or row.get("line_text") or "").strip()
        source_url = str(row.get("source_url", "")).strip()
        href = str(row.get("href", "")).strip()

        if node_type == "noise" or not label:
            continue

        if node_type in type_rank:
            current_rank = type_rank[node_type]
            while stack and type_rank.get(stack[-1]["node_type"], 999) >= current_rank:
                stack.pop()
            stack.append({"node_type": node_type, "label": label, "slug": slugify(label)})
            hierarchy_path = " / ".join(item["label"] for item in stack)
        elif node_type == "heading":
            hierarchy_path = build_path(stack, label)
        elif node_type == "article":
            hierarchy_path = build_path(stack, label)
        else:
            hierarchy_path = " / ".join(item["label"] for item in stack)

        node = {
            "node_type": node_type,
            "label": label,
            "title": label,
            "hierarchy_path": hierarchy_path,
            "order_index": order_index,
            "source_url": source_url,
            "line_no": row.get("line_no", 0),
            "confidence": row.get("confidence", 0.0),
            "needs_review": row.get("needs_review", False),
            "href": href,
        }
        nodes.append(node)

        if node_type == "article":
            article_rows.append(
                {
                    "article_number": extract_article_number(label),
                    "article_label": label,
                    "hierarchy_path": hierarchy_path,
                    "source_url": source_url,
                    "article_url": href,
                    "order_index": order_index,
                    "line_no": row.get("line_no", 0),
                }
            )

    write_jsonl(args.nodes_output_path, nodes)
    write_jsonl(args.article_index_output_path, article_rows)

    counts: dict[str, int] = {}
    for node in nodes:
        node_type = node["node_type"]
        counts[node_type] = counts.get(node_type, 0) + 1

    report = {
        "input_path": str(args.input_path),
        "hierarchy_nodes_output_path": str(args.nodes_output_path),
        "article_index_output_path": str(args.article_index_output_path),
        "node_count": len(nodes),
        "article_node_count": len(article_rows),
        "counts_by_type": counts,
    }
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
