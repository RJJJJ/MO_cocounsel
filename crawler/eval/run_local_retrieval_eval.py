#!/usr/bin/env python3
"""Run local retrieval evaluation on top of the Macau court BM25 prototype."""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from crawler.retrieval.local_bm25_query_prototype import (
    BM25_CHUNKS_PATH,
    LocalBM25Index,
    MixedTokenizer,
    read_jsonl,
)

DEFAULT_QUERY_SET_PATH = Path("data/eval/macau_court_query_test_set.jsonl")
DEFAULT_REPORT_PATH = Path("data/eval/macau_court_eval_report.txt")


def normalize_case_number(case_number: str) -> str:
    return re.sub(r"\s+", "", (case_number or "").lower())


def load_query_test_set(path: Path) -> list[dict[str, Any]]:
    queries: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file_obj:
        for line_no, line in enumerate(file_obj, start=1):
            line = line.strip()
            if not line:
                continue

            payload = json.loads(line)
            required_fields = ["query_id", "query", "query_type", "expected_case_numbers", "notes"]
            missing = [field for field in required_fields if field not in payload]
            if missing:
                raise ValueError(f"Invalid test set row at line {line_no}, missing fields: {missing}")

            if not isinstance(payload["expected_case_numbers"], list):
                raise ValueError(f"Invalid expected_case_numbers at line {line_no}; list required")

            queries.append(payload)

    return queries


def first_hit_rank(expected: set[str], ranked_cases: list[str]) -> int | None:
    for idx, case_number in enumerate(ranked_cases, start=1):
        if normalize_case_number(case_number) in expected:
            return idx
    return None


def build_report_lines(
    query_results: list[dict[str, Any]],
    top_k: int,
    total_bm25_records: int,
    tokenizer_strategy: str,
    query_set_path: Path,
) -> list[str]:
    total_queries = len(query_results)
    with_expectation = [item for item in query_results if item["has_expectation"]]

    exact_hits = sum(1 for item in with_expectation if item["hit"])
    hit_rate = (exact_hits / len(with_expectation)) if with_expectation else 0.0

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in query_results:
        grouped[result["query_type"]].append(result)

    lines = [
        "Macau Court Local Retrieval Evaluation Report",
        f"bm25_input_path: {BM25_CHUNKS_PATH}",
        f"query_test_set_path: {query_set_path}",
        f"total_bm25_records_loaded: {total_bm25_records}",
        f"tokenizer_strategy_used: {tokenizer_strategy}",
        f"top_k_used: {top_k}",
        f"total_queries_loaded: {total_queries}",
        f"total_queries_evaluated: {total_queries}",
        f"queries_with_expected_cases: {len(with_expectation)}",
        f"exact_case_hit_count: {exact_hits}",
        f"hit@{top_k}: {exact_hits}/{len(with_expectation) if with_expectation else 0} ({hit_rate:.2%})",
        "",
        "hit_by_query_type:",
    ]

    for query_type in sorted(grouped):
        rows = grouped[query_type]
        rows_with_expectation = [row for row in rows if row["has_expectation"]]
        type_hits = sum(1 for row in rows_with_expectation if row["hit"])
        denominator = len(rows_with_expectation)
        rate = (type_hits / denominator) if denominator else 0.0
        lines.append(f"  - {query_type}: {type_hits}/{denominator} ({rate:.2%})")

    lines.extend(["", "per_query_summary:"])

    for row in query_results:
        lines.append(
            "  - "
            f"query_id={row['query_id']} | type={row['query_type']} | hit={row['hit']} | "
            f"first_hit_rank={row['first_hit_rank']} | expected={row['expected_case_numbers']} | "
            f"top_cases={row['top_cases']} | query={row['query']}"
        )

    lines.append("")
    lines.append(f"local_retrieval_evaluation_appears_successful: {hit_rate >= 0.50 and len(with_expectation) >= 5}")
    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local retrieval evaluation for Macau court BM25 pipeline")
    parser.add_argument("--bm25-path", type=Path, default=BM25_CHUNKS_PATH, help="BM25 chunks JSONL path")
    parser.add_argument("--query-set-path", type=Path, default=DEFAULT_QUERY_SET_PATH, help="query test set JSONL path")
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH, help="evaluation report output path")
    parser.add_argument("--top-k", type=int, default=10, help="top-k for BM25 retrieval")
    parser.add_argument(
        "--tokenizer",
        choices=["deterministic", "auto", "jieba"],
        default="deterministic",
        help="tokenizer backend (default: deterministic)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.bm25_path.exists():
        raise FileNotFoundError(f"BM25 chunks file not found: {args.bm25_path}")
    if not args.query_set_path.exists():
        raise FileNotFoundError(f"Query test set file not found: {args.query_set_path}")

    bm25_records = read_jsonl(args.bm25_path)
    query_set = load_query_test_set(args.query_set_path)

    tokenizer = MixedTokenizer(mode=args.tokenizer)
    bm25_index = LocalBM25Index(records=bm25_records, tokenizer=tokenizer)

    query_results: list[dict[str, Any]] = []
    for query_row in query_set:
        hits, _ = bm25_index.search(query=query_row["query"], top_k=args.top_k)
        ranked_cases: list[str] = []
        for hit in hits:
            case = hit.authoritative_case_number
            if case and case not in ranked_cases:
                ranked_cases.append(case)

        expected_cases = [str(case) for case in query_row.get("expected_case_numbers", [])]
        normalized_expected = {normalize_case_number(case) for case in expected_cases}
        has_expectation = bool(normalized_expected)

        matched_rank = first_hit_rank(normalized_expected, ranked_cases) if has_expectation else None
        hit = matched_rank is not None if has_expectation else False

        query_results.append(
            {
                "query_id": query_row["query_id"],
                "query": query_row["query"],
                "query_type": query_row["query_type"],
                "expected_case_numbers": expected_cases,
                "top_cases": ranked_cases,
                "first_hit_rank": matched_rank,
                "hit": hit,
                "has_expectation": has_expectation,
            }
        )

    report_lines = build_report_lines(
        query_results=query_results,
        top_k=args.top_k,
        total_bm25_records=len(bm25_records),
        tokenizer_strategy=bm25_index.tokenizer_strategy_used,
        query_set_path=args.query_set_path,
    )

    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    with_expectation_count = sum(1 for row in query_results if row["has_expectation"])
    hit_count = sum(1 for row in query_results if row["hit"])
    hit_rate = (hit_count / with_expectation_count) if with_expectation_count else 0.0
    success = hit_rate >= 0.50 and with_expectation_count >= 5

    print(f"total queries loaded: {len(query_set)}")
    print(f"total queries evaluated: {len(query_results)}")
    print(f"hit@{args.top_k} summary: {hit_count}/{with_expectation_count} ({hit_rate:.2%})")
    print(f"local retrieval evaluation appears successful: {success}")
    print(f"evaluation report written to: {args.report_path}")


if __name__ == "__main__":
    main()
