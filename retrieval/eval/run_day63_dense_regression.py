#!/usr/bin/env python3
"""Run Day 63 dense retrieval baseline against Day 61 query pack."""

from __future__ import annotations

import argparse
import sys
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from crawler.retrieval.dense_embedding_baseline import (
    DENSE_BASELINE_ARTIFACT_PATH,
    DAY63_DENSE_MODEL_CONFIG,
    DenseSearchHit,
    build_or_load_dense_index,
)
from retrieval.eval.run_day61_regression_pack import evaluate_pass_rule, load_query_pack

DEFAULT_QUERY_PACK_PATH = Path("retrieval/eval/day61_regression_queries.json")
DEFAULT_RESULTS_PATH = Path("data/eval/day63_dense_retrieval_results.json")
DEFAULT_SUMMARY_PATH = Path("data/eval/day63_dense_retrieval_summary.txt")


@dataclass(frozen=True)
class Day63DenseResult:
    query_id: str
    query_text: str
    route_hint: str | None
    expected_behavior: str
    pass_rule: dict[str, Any]
    retrieval_mode_used: str
    top_k_requested: int
    top_hits: list[dict[str, Any]]
    passed: bool
    failure_reason: str | None


def _normalize_hit(hit: DenseSearchHit) -> dict[str, Any]:
    return {
        "chunk_id": hit.chunk_id,
        "score": round(float(hit.score), 6),
        "retrieval_source": "dense_day63_baseline",
        "authoritative_case_number": hit.authoritative_case_number,
        "authoritative_decision_date": hit.authoritative_decision_date,
        "court": hit.court,
        "language": hit.language,
        "case_type": hit.case_type,
        "chunk_text_preview": hit.chunk_text_preview,
        "pdf_url": hit.pdf_url,
        "text_url_or_action": hit.text_url_or_action,
    }


def build_summary_text(
    run_started_at: str,
    query_pack_path: Path,
    artifact_path: Path,
    total_queries: int,
    passed_queries: int,
    failed_queries: int,
    pass_rate: float,
    per_query_results: list[Day63DenseResult],
) -> str:
    lines = [
        "Day 63 Dense Retrieval Regression Summary",
        f"run_started_at_utc: {run_started_at}",
        f"query_pack_path: {query_pack_path}",
        f"artifact_path: {artifact_path}",
        f"model_key: {DAY63_DENSE_MODEL_CONFIG.model_key}",
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
    parser = argparse.ArgumentParser(description="Run Day 63 dense retrieval regression")
    parser.add_argument("--query-pack", type=Path, default=DEFAULT_QUERY_PACK_PATH)
    parser.add_argument("--top-k", type=int, default=7)
    parser.add_argument("--artifact", type=Path, default=DENSE_BASELINE_ARTIFACT_PATH)
    parser.add_argument("--rebuild-index", action="store_true")
    parser.add_argument("--output-json", type=Path, default=DEFAULT_RESULTS_PATH)
    parser.add_argument("--output-summary", type=Path, default=DEFAULT_SUMMARY_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_started_at = datetime.now(timezone.utc).isoformat()
    query_specs = load_query_pack(args.query_pack)

    dense_index = build_or_load_dense_index(artifact_path=args.artifact, rebuild=args.rebuild_index)

    per_query_results: list[Day63DenseResult] = []
    for query_spec in query_specs:
        hits = dense_index.search(query=query_spec["query_text"], top_k=args.top_k)
        top_hits = [_normalize_hit(hit) for hit in hits]
        passed, failure_reason = evaluate_pass_rule(query_spec["pass_rule"], top_hits)

        per_query_results.append(
            Day63DenseResult(
                query_id=query_spec["query_id"],
                query_text=query_spec["query_text"],
                route_hint=query_spec.get("route_hint"),
                expected_behavior=query_spec["expected_behavior"],
                pass_rule=query_spec["pass_rule"],
                retrieval_mode_used=f"dense_only|{dense_index.model_key}",
                top_k_requested=args.top_k,
                top_hits=top_hits,
                passed=passed,
                failure_reason=failure_reason,
            )
        )

    total_queries = len(per_query_results)
    passed_queries = sum(1 for item in per_query_results if item.passed)
    failed_queries = total_queries - passed_queries
    pass_rate = (passed_queries / total_queries) if total_queries else 0.0

    payload = {
        "run_started_at_utc": run_started_at,
        "query_pack_path": str(args.query_pack),
        "artifact_path": str(args.artifact),
        "model_key": DAY63_DENSE_MODEL_CONFIG.model_key,
        "top_k": args.top_k,
        "total_queries": total_queries,
        "passed": passed_queries,
        "failed": failed_queries,
        "pass_rate": round(pass_rate, 6),
        "results": [asdict(item) for item in per_query_results],
    }

    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    summary_text = build_summary_text(
        run_started_at=run_started_at,
        query_pack_path=args.query_pack,
        artifact_path=args.artifact,
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
