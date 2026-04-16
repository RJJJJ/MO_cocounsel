#!/usr/bin/env python3
"""Day 36: refine Portuguese / mixed-language query routing and normalization.

Scope constraints:
- local-only
- no database
- no external API
- no vector retrieval
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from crawler.retrieval.search_router_layer import DeterministicSearchRouter, SearchRouterResult

DEMO_REPORT_PATH = Path("data/eval/portuguese_mixed_query_routing_demo_report.txt")

DEFAULT_DEMO_QUERIES = [
    "erro ostensivo, legis artis",
    "processo n o 578/2025 recurso em matéria cível",
    "假釋 liberdade condicional",
    "processo 253/2026 liberdade condicional 假釋",
]


@dataclass(frozen=True)
class PortugueseMixedRoutingDemoResult:
    query_received: str
    normalized_query: str
    detected_language_signals: str
    query_type: str
    routing_strategy: str
    retrieval_mode: str
    portuguese_mixed_query_routing_refinement_appears_successful: bool
    router_result: SearchRouterResult


def evaluate_success(router_result: SearchRouterResult) -> bool:
    normalized = router_result.normalized_query.lower()
    contains_pt_or_mixed = (
        any(token in normalized for token in ("legis artis", "erro ostensivo", "liberdade condicional", "processo"))
        or "mixed_language=true" in router_result.language_signal_summary.lower()
    )

    if not contains_pt_or_mixed:
        return True

    if router_result.query_type == "ambiguous_or_noisy":
        return False

    return router_result.routing_strategy in {
        "language_aware_bm25_path",
        "exact_case_number_heavy_with_pt_context_retention",
        "prefer_exact_case_number_path_then_hybrid_fallback",
    }


def run_demo_queries(queries: list[str]) -> list[PortugueseMixedRoutingDemoResult]:
    router = DeterministicSearchRouter()
    results: list[PortugueseMixedRoutingDemoResult] = []

    for query in queries:
        routed = router.route(query)
        results.append(
            PortugueseMixedRoutingDemoResult(
                query_received=query,
                normalized_query=routed.normalized_query,
                detected_language_signals=routed.language_signal_summary,
                query_type=routed.query_type,
                routing_strategy=routed.routing_strategy,
                retrieval_mode=routed.retrieval_mode,
                portuguese_mixed_query_routing_refinement_appears_successful=evaluate_success(routed),
                router_result=routed,
            )
        )

    return results


def write_demo_report(results: list[PortugueseMixedRoutingDemoResult], output: Path) -> None:
    lines = ["Portuguese / Mixed Query Routing Demo Report - Day 36"]
    for idx, result in enumerate(results, start=1):
        lines.extend(
            [
                "",
                f"=== demo case {idx} ===",
                f"query received: {result.query_received}",
                f"normalized query: {result.normalized_query}",
                f"detected language signals: {result.detected_language_signals}",
                f"query_type: {result.query_type}",
                f"routing_strategy: {result.routing_strategy}",
                f"retrieval_mode: {result.retrieval_mode}",
                (
                    "whether portuguese/mixed query routing refinement appears successful: "
                    f"{result.portuguese_mixed_query_routing_refinement_appears_successful}"
                ),
                "router_result_json:",
                json.dumps(asdict(result.router_result), ensure_ascii=False, indent=2),
            ]
        )

    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local Portuguese/mixed query routing refinement demo")
    parser.add_argument(
        "--query",
        action="append",
        default=[],
        help="query to route. If omitted, default Day 36 demo queries are used.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEMO_REPORT_PATH,
        help="local output report path",
    )
    parser.add_argument("--json", action="store_true", help="print JSON output")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    queries = args.query or DEFAULT_DEMO_QUERIES
    results = run_demo_queries(queries)

    write_demo_report(results, args.output)

    for result in results:
        print("---")
        print(f"query received: {result.query_received}")
        print(f"normalized query: {result.normalized_query}")
        print(f"detected language signals: {result.detected_language_signals}")
        print(f"query_type: {result.query_type}")
        print(f"routing_strategy: {result.routing_strategy}")
        print(f"retrieval_mode: {result.retrieval_mode}")
        print(
            "whether portuguese/mixed query routing refinement appears successful: "
            f"{result.portuguese_mixed_query_routing_refinement_appears_successful}"
        )

    if args.json:
        print(json.dumps([asdict(item) for item in results], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
