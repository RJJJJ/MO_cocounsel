#!/usr/bin/env python3
"""Build a local retrieval query test set for the Macau court BM25 prototype."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

DEFAULT_BM25_PATH = Path("data/corpus/prepared/macau_court_cases/bm25_chunks.jsonl")
DEFAULT_OUTPUT_PATH = Path("data/eval/macau_court_query_test_set.jsonl")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file_obj:
        for line in file_obj:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def normalize_case_number(case_number: str) -> str:
    return re.sub(r"\s+", "", (case_number or "").lower())


def build_case_text_map(records: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    grouped_texts: dict[str, list[str]] = defaultdict(list)
    grouped_languages: dict[str, set[str]] = defaultdict(set)

    for record in records:
        case_number = str(record.get("authoritative_case_number", "")).strip()
        if not case_number:
            continue

        grouped_texts[case_number].append(str(record.get("bm25_text", "")))
        grouped_texts[case_number].append(str(record.get("chunk_text", "")))
        grouped_languages[case_number].add(str(record.get("language", "")).strip().lower())

    case_text_map: dict[str, dict[str, Any]] = {}
    for case_number, texts in grouped_texts.items():
        merged = "\n".join(texts)
        case_text_map[case_number] = {
            "case_number": case_number,
            "normalized_case_number": normalize_case_number(case_number),
            "text": merged,
            "text_lower": merged.lower(),
            "languages": grouped_languages.get(case_number, set()),
        }

    return case_text_map


def find_case_numbers(
    case_text_map: dict[str, dict[str, Any]],
    must_contain: list[str],
    preferred_language: str | None = None,
    max_matches: int = 3,
) -> list[str]:
    if not must_contain:
        return []

    lowered_terms = [term.lower() for term in must_contain if term.strip()]
    matches: list[str] = []
    for case_number in sorted(case_text_map):
        payload = case_text_map[case_number]

        if preferred_language and preferred_language not in payload["languages"]:
            continue

        haystack = payload["text_lower"]
        if all(term in haystack for term in lowered_terms):
            matches.append(case_number)

        if len(matches) >= max_matches:
            break

    return matches


def build_test_set(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    case_text_map = build_case_text_map(records)

    query_specs: list[dict[str, Any]] = [
        {
            "query_id": "Q001",
            "query": "假釋",
            "query_type": "legal_concept_zh",
            "must_contain": ["假釋"],
            "expected_language": "zh",
            "notes": "中文法律概念詞：假釋。",
        },
        {
            "query_id": "Q002",
            "query": "量刑過重",
            "query_type": "legal_concept_zh",
            "must_contain": ["量刑過重"],
            "expected_language": "zh",
            "notes": "中文法律概念詞：量刑過重。",
        },
        {
            "query_id": "Q003",
            "query": "誹謗",
            "query_type": "legal_concept_zh",
            "must_contain": ["誹謗"],
            "expected_language": "zh",
            "notes": "中文法律概念詞：誹謗。",
        },
        {
            "query_id": "Q004",
            "query": "違令",
            "query_type": "legal_concept_zh",
            "must_contain": ["違令"],
            "expected_language": "zh",
            "notes": "中文法律概念詞：違令。",
        },
        {
            "query_id": "Q005",
            "query": "合同之不能履行",
            "query_type": "issue_fact_zh",
            "must_contain": ["合同", "不能履行"],
            "expected_language": "zh",
            "notes": "中文爭點詞：合同與不能履行。",
        },
        {
            "query_id": "Q006",
            "query": "損害賠償",
            "query_type": "issue_fact_zh",
            "must_contain": ["損害賠償"],
            "expected_language": "zh",
            "notes": "中文爭點詞：損害賠償。",
        },
        {
            "query_id": "Q007",
            "query": "加重詐騙",
            "query_type": "issue_fact_zh",
            "must_contain": ["加重詐騙"],
            "expected_language": "zh",
            "notes": "中文爭點詞：加重詐騙。",
        },
        {
            "query_id": "Q008",
            "query": "79/2025",
            "query_type": "case_number_lookup",
            "expected_case_numbers": [],
            "notes": "案件編號查詢（樣本可能不存在，用於觀察無命中行為）。",
        },
        {
            "query_id": "Q009",
            "query": "253/2026",
            "query_type": "case_number_lookup",
            "expected_case_numbers": ["253/2026"],
            "notes": "案件編號查詢（應可直接命中）。",
        },
        {
            "query_id": "Q010",
            "query": "processo n o 578/2025 recurso em matéria cível",
            "query_type": "portuguese_or_mixed",
            "must_contain": ["processo", "578/2025", "recurso"],
            "expected_language": "pt",
            "notes": "葡文查詢樣本（程序號 + recurso）。",
        },
        {
            "query_id": "Q011",
            "query": "假釋 liberdade condicional",
            "query_type": "portuguese_or_mixed",
            "must_contain": ["condicional"],
            "expected_language": "pt",
            "notes": "中葡混合查詢樣本，用於測試跨語詞匹配。",
        },
        {
            "query_id": "Q012",
            "query": "上訴",
            "query_type": "ambiguous_or_noisy",
            "expected_case_numbers": [],
            "notes": "高頻模糊詞，預期結果分散。",
        },
        {
            "query_id": "Q013",
            "query": "公司",
            "query_type": "ambiguous_or_noisy",
            "expected_case_numbers": [],
            "notes": "可疑/模糊查詢，用於觀察 BM25 baseline 限制。",
        },
    ]

    results: list[dict[str, Any]] = []
    for spec in query_specs:
        expected_case_numbers = spec.get("expected_case_numbers")
        if expected_case_numbers is None:
            expected_case_numbers = find_case_numbers(
                case_text_map=case_text_map,
                must_contain=spec.get("must_contain", []),
                preferred_language=spec.get("expected_language"),
                max_matches=3,
            )
            if not expected_case_numbers and spec.get("expected_language"):
                expected_case_numbers = find_case_numbers(
                    case_text_map=case_text_map,
                    must_contain=spec.get("must_contain", []),
                    preferred_language=None,
                    max_matches=3,
                )

        entry = {
            "query_id": spec["query_id"],
            "query": spec["query"],
            "query_type": spec["query_type"],
            "expected_case_numbers": expected_case_numbers,
            "notes": spec["notes"],
        }

        expected_language = spec.get("expected_language")
        if expected_language:
            entry["expected_language"] = expected_language

        results.append(entry)

    return results


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_obj:
        for row in rows:
            file_obj.write(json.dumps(row, ensure_ascii=False) + "\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build local query test set for Macau court retrieval evaluation")
    parser.add_argument("--bm25-path", type=Path, default=DEFAULT_BM25_PATH, help="input BM25 chunks JSONL path")
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH, help="output query test set JSONL path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.bm25_path.exists():
        raise FileNotFoundError(f"BM25 chunks file not found: {args.bm25_path}")

    records = read_jsonl(args.bm25_path)
    query_set = build_test_set(records)
    write_jsonl(args.output_path, query_set)

    has_expectations = sum(1 for item in query_set if item.get("expected_case_numbers"))
    print(f"total bm25 records loaded: {len(records)}")
    print(f"total queries generated: {len(query_set)}")
    print(f"queries with expected cases: {has_expectations}")
    print(f"query test set written to: {args.output_path}")


if __name__ == "__main__":
    main()
