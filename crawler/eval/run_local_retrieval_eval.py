#!/usr/bin/env python3
"""Run local retrieval evaluation with baseline vs normalized Chinese legal queries."""

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

from crawler.retrieval.improve_chinese_legal_query_normalization import ChineseLegalQueryNormalizer
from crawler.retrieval.local_bm25_query_prototype import BM25_CHUNKS_PATH, LocalBM25Index, MixedTokenizer, read_jsonl

DEFAULT_QUERY_SET_PATH = Path("data/eval/macau_court_query_test_set.jsonl")
DEFAULT_REPORT_PATH = Path("data/eval/macau_court_eval_report_normalized.txt")


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


def evaluate_mode(
    bm25_records: list[dict[str, Any]],
    query_set: list[dict[str, Any]],
    top_k: int,
    tokenizer_mode: str,
    use_normalization: bool,
) -> dict[str, Any]:
    tokenizer = MixedTokenizer(mode=tokenizer_mode)
    normalizer = ChineseLegalQueryNormalizer() if use_normalization else None
    bm25_index = LocalBM25Index(records=bm25_records, tokenizer=tokenizer, query_normalizer=normalizer)

    query_results: list[dict[str, Any]] = []
    normalization_rules_used: set[str] = set()

    for query_row in query_set:
        hits, _, normalized_query = bm25_index.search(query=query_row["query"], top_k=top_k)

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

        if normalized_query is not None:
            normalization_rules_used.update(normalized_query.applied_rules)

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
                "normalized_query": normalized_query.normalized_query if normalized_query else None,
                "expanded_query": normalized_query.expanded_query if normalized_query else None,
                "normalization_rules": normalized_query.applied_rules if normalized_query else [],
            }
        )

    with_expectation = [item for item in query_results if item["has_expectation"]]
    hit_count = sum(1 for item in with_expectation if item["hit"])
    hit_rate = (hit_count / len(with_expectation)) if with_expectation else 0.0

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in query_results:
        grouped[result["query_type"]].append(result)

    return {
        "query_results": query_results,
        "with_expectation": len(with_expectation),
        "hit_count": hit_count,
        "hit_rate": hit_rate,
        "grouped": grouped,
        "tokenizer_strategy": bm25_index.tokenizer_strategy_used,
        "normalization_strategy": sorted(normalization_rules_used),
    }


def build_report_lines(
    *,
    top_k: int,
    total_bm25_records: int,
    query_set_path: Path,
    baseline: dict[str, Any],
    normalized: dict[str, Any],
) -> list[str]:
    improved = normalized["hit_rate"] > baseline["hit_rate"]

    lines = [
        "Macau Court Local Retrieval Evaluation Report (Baseline vs Normalized)",
        f"bm25_input_path: {BM25_CHUNKS_PATH}",
        f"query_test_set_path: {query_set_path}",
        f"total_bm25_records_loaded: {total_bm25_records}",
        f"top_k_used: {top_k}",
        f"total_queries_evaluated: {len(baseline['query_results'])}",
        f"baseline_tokenizer_strategy: {baseline['tokenizer_strategy']}",
        f"normalized_tokenizer_strategy: {normalized['tokenizer_strategy']}",
        (
            "normalization_strategy_used: "
            + (", ".join(normalized["normalization_strategy"]) if normalized["normalization_strategy"] else "none")
        ),
        "",
        f"baseline_hit@{top_k}: {baseline['hit_count']}/{baseline['with_expectation']} ({baseline['hit_rate']:.2%})",
        f"normalized_hit@{top_k}: {normalized['hit_count']}/{normalized['with_expectation']} ({normalized['hit_rate']:.2%})",
        f"normalized_retrieval_appears_improved: {improved}",
        "",
        "hit_by_query_type_before_after:",
    ]

    all_types = sorted(set(baseline["grouped"]) | set(normalized["grouped"]))
    for query_type in all_types:
        b_rows = [r for r in baseline["grouped"].get(query_type, []) if r["has_expectation"]]
        n_rows = [r for r in normalized["grouped"].get(query_type, []) if r["has_expectation"]]
        b_hit = sum(1 for r in b_rows if r["hit"])
        n_hit = sum(1 for r in n_rows if r["hit"])
        b_rate = (b_hit / len(b_rows)) if b_rows else 0.0
        n_rate = (n_hit / len(n_rows)) if n_rows else 0.0
        lines.append(
            f"  - {query_type}: baseline={b_hit}/{len(b_rows)} ({b_rate:.2%}) | "
            f"normalized={n_hit}/{len(n_rows)} ({n_rate:.2%})"
        )

    lines.extend(["", "per_query_before_after:"])
    normalized_by_id = {item["query_id"]: item for item in normalized["query_results"]}

    for base_row in baseline["query_results"]:
        norm_row = normalized_by_id[base_row["query_id"]]
        lines.append(
            "  - "
            f"query_id={base_row['query_id']} | type={base_row['query_type']} | "
            f"baseline_hit={base_row['hit']}@{base_row['first_hit_rank']} | "
            f"normalized_hit={norm_row['hit']}@{norm_row['first_hit_rank']} | "
            f"query={base_row['query']} | normalized_query={norm_row['normalized_query']} | "
            f"expanded_query={norm_row['expanded_query']} | expected={base_row['expected_case_numbers']}"
        )

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

    baseline = evaluate_mode(
        bm25_records=bm25_records,
        query_set=query_set,
        top_k=args.top_k,
        tokenizer_mode=args.tokenizer,
        use_normalization=False,
    )
    normalized = evaluate_mode(
        bm25_records=bm25_records,
        query_set=query_set,
        top_k=args.top_k,
        tokenizer_mode=args.tokenizer,
        use_normalization=True,
    )

    report_lines = build_report_lines(
        top_k=args.top_k,
        total_bm25_records=len(bm25_records),
        query_set_path=args.query_set_path,
        baseline=baseline,
        normalized=normalized,
    )

    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    improved = normalized["hit_rate"] > baseline["hit_rate"]

    print(
        "normalization strategy used: "
        + (", ".join(normalized["normalization_strategy"]) if normalized["normalization_strategy"] else "none")
    )
    print(f"total queries evaluated: {len(query_set)}")
    print(f"baseline hit@{args.top_k}: {baseline['hit_count']}/{baseline['with_expectation']} ({baseline['hit_rate']:.2%})")
    print(
        f"normalized hit@{args.top_k}: {normalized['hit_count']}/{normalized['with_expectation']} "
        f"({normalized['hit_rate']:.2%})"
    )
    print(f"whether normalized retrieval appears improved: {improved}")
    print(f"evaluation report written to: {args.report_path}")


if __name__ == "__main__":
    main()
