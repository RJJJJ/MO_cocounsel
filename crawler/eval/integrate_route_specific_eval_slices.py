#!/usr/bin/env python3
"""Day 37: integrate route-specific evaluation slices for local retrieval pipeline.

Scope constraints:
- local-only
- no database
- no external API
- no vector retrieval
- evaluation slicing + reporting only
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from crawler.retrieval.hybrid_retrieval_skeleton import build_default_hybrid_retriever
from crawler.retrieval.hybrid_retrieval_with_decomposition import DecompositionAwareHybridRetriever
from crawler.retrieval.refine_exact_case_number_lookup import BM25_CHUNKS_PATH, ExactCaseNumberRetriever, load_records
from crawler.retrieval.search_router_layer import DeterministicSearchRouter, SearchRouterResult

DEFAULT_QUERY_SET_PATH = Path("data/eval/macau_court_query_test_set.jsonl")
DEFAULT_REPORT_PATH = Path("data/eval/route_specific_eval_report.txt")
MIN_SAMPLE_SIZE_NOTE_THRESHOLD = 3

SLICE_NAMES = (
    "case_number_lookup",
    "single_legal_concept",
    "multi_issue_legal_query",
    "mixed_fact_legal_query",
    "portuguese_or_mixed",
    "ambiguous_or_noisy",
)


@dataclass(frozen=True)
class QueryEvalResult:
    query_id: str
    query: str
    router_query_type: str
    routing_strategy: str
    retrieval_mode: str
    assigned_slice: str
    expected_case_numbers: list[str]
    ranked_case_numbers: list[str]
    has_expectation: bool
    exact_case_hit: bool
    hit_at_k: bool


@dataclass(frozen=True)
class SliceSummary:
    slice_name: str
    total_queries: int
    queries_with_expected_cases: int
    exact_case_hit_count: int
    hit_at_k: float
    sample_size_note: str


def normalize_case_number(case_number: str) -> str:
    return re.sub(r"\s+", "", (case_number or "").lower())


def load_query_test_set(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file_obj:
        for line_no, line in enumerate(file_obj, start=1):
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            required_fields = ["query_id", "query", "expected_case_numbers"]
            missing = [field for field in required_fields if field not in payload]
            if missing:
                raise ValueError(f"Invalid test set row at line {line_no}, missing fields: {missing}")
            if not isinstance(payload["expected_case_numbers"], list):
                raise ValueError(f"Invalid expected_case_numbers at line {line_no}; list required")
            rows.append(payload)
    return rows


def map_router_type_to_slice(router_query_type: str) -> str:
    if router_query_type in {"case_number_lookup", "case_number_lookup_pt_mixed"}:
        return "case_number_lookup"
    if router_query_type == "single_legal_concept":
        return "single_legal_concept"
    if router_query_type == "multi_issue_legal_query":
        return "multi_issue_legal_query"
    if router_query_type == "mixed_fact_legal_query":
        return "mixed_fact_legal_query"
    if router_query_type in {"portuguese_or_mixed", "portuguese_or_mixed_multi_issue"}:
        return "portuguese_or_mixed"
    return "ambiguous_or_noisy"


def extract_case_numbers_from_hits(hits: list[Any]) -> list[str]:
    ranked: list[str] = []
    seen: set[str] = set()
    for hit in hits:
        case_number = str(getattr(hit, "authoritative_case_number", "") or "").strip()
        if not case_number:
            continue
        normalized = normalize_case_number(case_number)
        if normalized in seen:
            continue
        seen.add(normalized)
        ranked.append(case_number)
    return ranked


def run_retrieval_by_route(
    router_result: SearchRouterResult,
    top_k: int,
    *,
    direct_retriever: Any,
    decomposition_retriever: DecompositionAwareHybridRetriever,
    exact_retriever: ExactCaseNumberRetriever,
) -> list[str]:
    normalized_query = router_result.normalized_query

    if router_result.retrieval_mode.startswith("exact_case_number_heavy"):
        exact_result = exact_retriever.retrieve(raw_query=normalized_query, top_k=top_k)
        return extract_case_numbers_from_hits(exact_result.hits)

    if router_result.decomposition_recommended:
        decomp_result = decomposition_retriever.retrieve(query=normalized_query, top_k=top_k, decompose=True)
        return extract_case_numbers_from_hits(decomp_result.hits)

    direct_result = direct_retriever.retrieve(query=normalized_query, top_k=top_k)
    return extract_case_numbers_from_hits(direct_result.hits)


def evaluate_queries(query_rows: list[dict[str, Any]], top_k: int, bm25_path: Path) -> list[QueryEvalResult]:
    router = DeterministicSearchRouter()
    direct_retriever = build_default_hybrid_retriever(enable_query_normalization=True)
    decomposition_retriever = DecompositionAwareHybridRetriever()
    exact_retriever = ExactCaseNumberRetriever(records=load_records(bm25_path))

    results: list[QueryEvalResult] = []

    for row in query_rows:
        router_result = router.route(str(row["query"]))
        ranked_cases = run_retrieval_by_route(
            router_result,
            top_k,
            direct_retriever=direct_retriever,
            decomposition_retriever=decomposition_retriever,
            exact_retriever=exact_retriever,
        )

        expected_cases = [str(item) for item in row.get("expected_case_numbers", [])]
        expected_normalized = {normalize_case_number(item) for item in expected_cases}
        hit = bool(expected_normalized) and any(
            normalize_case_number(item) in expected_normalized for item in ranked_cases[: max(top_k, 1)]
        )

        results.append(
            QueryEvalResult(
                query_id=str(row["query_id"]),
                query=str(row["query"]),
                router_query_type=router_result.query_type,
                routing_strategy=router_result.routing_strategy,
                retrieval_mode=router_result.retrieval_mode,
                assigned_slice=map_router_type_to_slice(router_result.query_type),
                expected_case_numbers=expected_cases,
                ranked_case_numbers=ranked_cases,
                has_expectation=bool(expected_normalized),
                exact_case_hit=hit,
                hit_at_k=hit,
            )
        )

    return results


def summarize_slices(results: list[QueryEvalResult]) -> list[SliceSummary]:
    summaries: list[SliceSummary] = []

    for slice_name in SLICE_NAMES:
        in_slice = [item for item in results if item.assigned_slice == slice_name]
        with_expected = [item for item in in_slice if item.has_expectation]
        exact_hit_count = sum(1 for item in with_expected if item.exact_case_hit)
        hit_rate = (exact_hit_count / len(with_expected)) if with_expected else 0.0

        note = "sample size is healthy"
        if len(in_slice) < MIN_SAMPLE_SIZE_NOTE_THRESHOLD:
            note = f"sample count is small (n={len(in_slice)})"

        summaries.append(
            SliceSummary(
                slice_name=slice_name,
                total_queries=len(in_slice),
                queries_with_expected_cases=len(with_expected),
                exact_case_hit_count=exact_hit_count,
                hit_at_k=hit_rate,
                sample_size_note=note,
            )
        )

    return summaries


def strongest_and_weakest_slice(summaries: list[SliceSummary]) -> tuple[SliceSummary | None, SliceSummary | None]:
    eligible = [item for item in summaries if item.queries_with_expected_cases > 0]
    if not eligible:
        return None, None

    strongest = max(eligible, key=lambda item: (item.hit_at_k, -item.total_queries, item.slice_name))
    weakest = min(eligible, key=lambda item: (item.hit_at_k, item.total_queries, item.slice_name))
    return strongest, weakest


def build_report_lines(
    *,
    query_set_path: Path,
    bm25_path: Path,
    top_k: int,
    query_results: list[QueryEvalResult],
    slice_summaries: list[SliceSummary],
    strongest: SliceSummary | None,
    weakest: SliceSummary | None,
) -> list[str]:
    lines = [
        "Route-Specific Local Retrieval Evaluation Report - Day 37",
        f"query_test_set_path: {query_set_path}",
        f"bm25_chunks_path: {bm25_path}",
        f"top_k: {top_k}",
        f"total_queries_evaluated: {len(query_results)}",
        f"number_of_slices_reported: {len(slice_summaries)}",
        (
            "strongest_slice: "
            + (f"{strongest.slice_name} ({strongest.exact_case_hit_count}/{strongest.queries_with_expected_cases}, {strongest.hit_at_k:.2%})" if strongest else "n/a")
        ),
        (
            "weakest_slice: "
            + (f"{weakest.slice_name} ({weakest.exact_case_hit_count}/{weakest.queries_with_expected_cases}, {weakest.hit_at_k:.2%})" if weakest else "n/a")
        ),
        (
            "route_specific_evaluation_slicing_appears_successful: "
            f"{bool(slice_summaries and len(query_results) > 0)}"
        ),
        "",
        "slice_summaries:",
    ]

    for summary in slice_summaries:
        lines.extend(
            [
                f"- slice: {summary.slice_name}",
                f"  total_queries: {summary.total_queries}",
                f"  queries_with_expected_cases: {summary.queries_with_expected_cases}",
                f"  exact_case_hit_count: {summary.exact_case_hit_count}",
                f"  hit@k: {summary.hit_at_k:.2%}",
                f"  notes: {summary.sample_size_note}",
            ]
        )

    lines.append("")
    lines.append("per_query_route_trace:")
    for item in query_results:
        lines.append(
            "- "
            f"query_id={item.query_id} | assigned_slice={item.assigned_slice} | "
            f"router_query_type={item.router_query_type} | routing_strategy={item.routing_strategy} | "
            f"retrieval_mode={item.retrieval_mode} | hit@{top_k}={item.hit_at_k} | "
            f"expected={item.expected_case_numbers} | top_cases={item.ranked_case_numbers}"
        )

    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Integrate route-specific retrieval evaluation slices (Day 37)")
    parser.add_argument("--query-set-path", type=Path, default=DEFAULT_QUERY_SET_PATH, help="query test set JSONL path")
    parser.add_argument("--bm25-path", type=Path, default=BM25_CHUNKS_PATH, help="BM25 chunks JSONL path")
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH, help="output report path")
    parser.add_argument("--top-k", type=int, default=10, help="hit@k threshold")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.query_set_path.exists():
        raise FileNotFoundError(f"Query test set file not found: {args.query_set_path}")
    if not args.bm25_path.exists():
        raise FileNotFoundError(f"BM25 chunks file not found: {args.bm25_path}")

    query_rows = load_query_test_set(args.query_set_path)
    query_results = evaluate_queries(query_rows=query_rows, top_k=args.top_k, bm25_path=args.bm25_path)
    slice_summaries = summarize_slices(query_results)
    strongest, weakest = strongest_and_weakest_slice(slice_summaries)

    report_lines = build_report_lines(
        query_set_path=args.query_set_path,
        bm25_path=args.bm25_path,
        top_k=args.top_k,
        query_results=query_results,
        slice_summaries=slice_summaries,
        strongest=strongest,
        weakest=weakest,
    )

    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"total queries evaluated: {len(query_results)}")
    print(f"number of slices reported: {len(slice_summaries)}")
    print(f"weakest slice: {weakest.slice_name if weakest else 'n/a'}")
    print(f"strongest slice: {strongest.slice_name if strongest else 'n/a'}")
    print(
        "whether route-specific evaluation slicing appears successful: "
        f"{bool(slice_summaries and len(query_results) > 0)}"
    )


if __name__ == "__main__":
    main()
