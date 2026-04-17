#!/usr/bin/env python3
"""Run Day 61 retrieval regression pack against the current local retrieval stack.

Scope:
- Reuse existing deterministic search router + retrieval flows.
- Produce repeatable pass/fail outputs for baseline comparison.
- Keep evaluation rules practical (top-k containment for concept queries).
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from crawler.retrieval.hybrid_retrieval_skeleton import HybridRetrievalResult, RetrievalHit, build_default_hybrid_retriever
from crawler.retrieval.hybrid_retrieval_with_decomposition import (
    DecompositionAwareHybridRetriever,
    DecompositionAwareRetrievalResult,
)
from crawler.retrieval.search_router_layer import DeterministicSearchRouter, SearchRouterResult

DEFAULT_QUERY_PACK_PATH = Path("retrieval/eval/day61_regression_queries.json")
DEFAULT_RESULTS_PATH = Path("data/eval/day61_regression_results.json")
DEFAULT_SUMMARY_PATH = Path("data/eval/day61_regression_summary.txt")


@dataclass(frozen=True)
class QueryExecutionResult:
    query_id: str
    query_text: str
    route_hint: str | None
    expected_behavior: str
    expected_case_numbers: list[str]
    expected_match_notes: str
    pass_rule: dict[str, Any]
    router_result: dict[str, Any]
    retrieval_mode_used: str
    top_k_requested: int
    top_hits: list[dict[str, Any]]
    passed: bool
    failure_reason: str | None


class Day61RegressionRunner:
    def __init__(self, top_k: int) -> None:
        self._top_k = top_k
        self._router = DeterministicSearchRouter()
        self._direct_retriever = build_default_hybrid_retriever(enable_query_normalization=True)
        self._decomposition_retriever = DecompositionAwareHybridRetriever()

    def run_query(self, query_spec: dict[str, Any]) -> QueryExecutionResult:
        router_result = self._router.route(query_spec["query_text"])
        top_hits, retrieval_mode_used = self._run_retrieval(router_result)
        passed, failure_reason = evaluate_pass_rule(query_spec["pass_rule"], top_hits)

        return QueryExecutionResult(
            query_id=query_spec["query_id"],
            query_text=query_spec["query_text"],
            route_hint=query_spec.get("route_hint"),
            expected_behavior=query_spec["expected_behavior"],
            expected_case_numbers=query_spec.get("expected_case_numbers", []),
            expected_match_notes=query_spec.get("expected_match_notes", ""),
            pass_rule=query_spec["pass_rule"],
            router_result=asdict(router_result),
            retrieval_mode_used=retrieval_mode_used,
            top_k_requested=self._top_k,
            top_hits=top_hits,
            passed=passed,
            failure_reason=failure_reason,
        )

    def _run_retrieval(self, router_result: SearchRouterResult) -> tuple[list[dict[str, Any]], str]:
        if router_result.decomposition_recommended:
            retrieval_result: DecompositionAwareRetrievalResult = self._decomposition_retriever.retrieve(
                query=router_result.normalized_query,
                top_k=self._top_k,
                decompose=True,
            )
            mode = f"{router_result.retrieval_mode}|decomposition_fanout"
            return [normalize_hit(hit) for hit in retrieval_result.hits], mode

        retrieval_result: HybridRetrievalResult = self._direct_retriever.retrieve(
            query=router_result.normalized_query,
            top_k=self._top_k,
        )
        mode = f"{router_result.retrieval_mode}|direct"
        return [normalize_hit(hit) for hit in retrieval_result.hits], mode


def normalize_hit(hit: RetrievalHit | Any) -> dict[str, Any]:
    return {
        "chunk_id": hit.chunk_id,
        "score": round(float(hit.score), 6),
        "retrieval_source": hit.retrieval_source,
        "authoritative_case_number": hit.authoritative_case_number,
        "authoritative_decision_date": hit.authoritative_decision_date,
        "court": hit.court,
        "language": hit.language,
        "case_type": hit.case_type,
        "chunk_text_preview": hit.chunk_text_preview,
        "pdf_url": hit.pdf_url,
        "text_url_or_action": hit.text_url_or_action,
    }


def evaluate_pass_rule(pass_rule: dict[str, Any], top_hits: list[dict[str, Any]]) -> tuple[bool, str | None]:
    rule_type = pass_rule.get("rule_type")

    if rule_type == "case_number_at_rank":
        rank = int(pass_rule["rank"])
        expected = pass_rule["case_number"]
        if len(top_hits) < rank:
            return False, f"Expected rank {rank} hit to be {expected}, but only {len(top_hits)} hits returned."
        actual = top_hits[rank - 1]["authoritative_case_number"]
        if actual == expected:
            return True, None
        return False, f"Expected rank {rank} case {expected}, got {actual}."

    if rule_type == "case_number_in_top_k":
        top_k = int(pass_rule["top_k"])
        expected = pass_rule["case_number"]
        window = [hit["authoritative_case_number"] for hit in top_hits[:top_k]]
        if expected in window:
            return True, None
        return False, f"Expected case {expected} in top {top_k}, got {window}."

    if rule_type == "any_case_number_in_top_k":
        top_k = int(pass_rule["top_k"])
        candidates = set(pass_rule["case_numbers"])
        window = [hit["authoritative_case_number"] for hit in top_hits[:top_k]]
        if any(case_number in candidates for case_number in window):
            return True, None
        return False, f"Expected any of {sorted(candidates)} in top {top_k}, got {window}."

    return False, f"Unsupported pass_rule.type: {rule_type}"


def load_query_pack(path: Path) -> list[dict[str, Any]]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError("Query pack must be a JSON array.")

    required_fields = {
        "query_id",
        "query_text",
        "route_hint",
        "expected_behavior",
        "pass_rule",
    }
    for index, item in enumerate(payload, start=1):
        missing = [field for field in required_fields if field not in item]
        if missing:
            raise ValueError(f"Query at index {index} is missing required fields: {missing}")
    return payload


def build_summary_text(
    run_started_at: str,
    query_pack_path: Path,
    total_queries: int,
    passed_queries: int,
    failed_queries: int,
    pass_rate: float,
    per_query_results: list[QueryExecutionResult],
) -> str:
    lines = [
        "Day 61 Retrieval Regression Summary",
        f"run_started_at_utc: {run_started_at}",
        f"query_pack_path: {query_pack_path}",
        f"total queries: {total_queries}",
        f"passed: {passed_queries}",
        f"failed: {failed_queries}",
        f"pass rate: {pass_rate:.2%}",
        "",
        "Per-query top results summary:",
    ]

    for result in per_query_results:
        lines.append(f"- {result.query_id} | passed={result.passed} | query={result.query_text}")
        lines.append(f"  route_hint={result.route_hint} | retrieval_mode_used={result.retrieval_mode_used}")

        for idx, hit in enumerate(result.top_hits, start=1):
            lines.append(
                "  "
                f"[{idx}] case={hit['authoritative_case_number']} "
                f"score={hit['score']:.6f} chunk_id={hit['chunk_id']}"
            )

        if result.failure_reason:
            lines.append(f"  failure_reason={result.failure_reason}")

    lines.append("")
    lines.append("Failure reasons:")
    failures = [item for item in per_query_results if not item.passed]
    if not failures:
        lines.append("- None")
    else:
        for item in failures:
            lines.append(f"- {item.query_id}: {item.failure_reason}")

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Day 61 retrieval regression query pack")
    parser.add_argument("--query-pack", type=Path, default=DEFAULT_QUERY_PACK_PATH)
    parser.add_argument("--top-k", type=int, default=7, help="Top-k retrieval hits per query")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_RESULTS_PATH)
    parser.add_argument("--output-summary", type=Path, default=DEFAULT_SUMMARY_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_started_at = datetime.now(timezone.utc).isoformat()
    query_specs = load_query_pack(args.query_pack)

    runner = Day61RegressionRunner(top_k=args.top_k)
    per_query_results = [runner.run_query(spec) for spec in query_specs]

    total_queries = len(per_query_results)
    passed_queries = sum(1 for item in per_query_results if item.passed)
    failed_queries = total_queries - passed_queries
    pass_rate = (passed_queries / total_queries) if total_queries else 0.0

    results_payload = {
        "run_started_at_utc": run_started_at,
        "query_pack_path": str(args.query_pack),
        "top_k": args.top_k,
        "total_queries": total_queries,
        "passed": passed_queries,
        "failed": failed_queries,
        "pass_rate": round(pass_rate, 6),
        "results": [asdict(item) for item in per_query_results],
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(results_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary_text = build_summary_text(
        run_started_at=run_started_at,
        query_pack_path=args.query_pack,
        total_queries=total_queries,
        passed_queries=passed_queries,
        failed_queries=failed_queries,
        pass_rate=pass_rate,
        per_query_results=per_query_results,
    )
    args.output_summary.parent.mkdir(parents=True, exist_ok=True)
    args.output_summary.write_text(summary_text, encoding="utf-8")

    print(f"total queries: {total_queries}")
    print(f"passed: {passed_queries}")
    print(f"failed: {failed_queries}")
    print(f"pass rate: {pass_rate:.2%}")
    print("per-query top results summary:")
    for item in per_query_results:
        top_cases = [hit["authoritative_case_number"] for hit in item.top_hits[: min(3, len(item.top_hits))]]
        print(f"- {item.query_id}: passed={item.passed} top_cases={top_cases}")

    print("failure reasons:")
    failures = [item for item in per_query_results if not item.passed]
    if not failures:
        print("- none")
    else:
        for item in failures:
            print(f"- {item.query_id}: {item.failure_reason}")

    print(f"results json: {args.output_json}")
    print(f"summary txt: {args.output_summary}")


if __name__ == "__main__":
    main()
