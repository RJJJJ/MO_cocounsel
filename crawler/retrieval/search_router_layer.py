#!/usr/bin/env python3
"""Deterministic local search router layer before retrieval.

Day 34 scope:
- local-only query classification + routing decision
- no database integration
- no external API calls
- no LLM integration
- no dense retrieval execution

This layer routes a query into the most suitable existing local retrieval flow.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from crawler.retrieval.hybrid_retrieval_skeleton import HybridRetrievalResult, build_default_hybrid_retriever
from crawler.retrieval.hybrid_retrieval_with_decomposition import (
    DecompositionAwareHybridRetriever,
    DecompositionAwareRetrievalResult,
)
from crawler.retrieval.portuguese_mixed_query_normalization import (
    PortugueseMixedNormalizationResult,
    PortugueseMixedQueryNormalizer,
)

DEMO_REPORT_PATH = Path("data/eval/search_router_demo_report.txt")

CASE_NUMBER_PATTERN = re.compile(r"\b\d{1,5}/\d{4}\b")
LEGAL_CONCEPT_HINTS = (
    "假釋",
    "假释",
    "量刑",
    "誹謗",
    "诽谤",
    "緩刑",
    "缓刑",
    "詐騙",
    "诈骗",
    "侵權",
    "侵权",
    "損害賠償",
    "损害赔偿",
    "上訴",
    "上诉",
    "撤銷",
    "撤销",
    "再審",
    "再审",
    "抗告",
)
FACT_HINTS = (
    "被告",
    "原告",
    "告訴人",
    "告诉人",
    "證據",
    "证据",
    "證人",
    "证人",
    "供述",
    "契約",
    "合同",
    "損失",
    "损失",
    "傷害",
    "伤害",
    "事實",
    "事实",
)
MULTI_ISSUE_CONNECTORS = ("與", "和", "及", "並", "且", "同時", "以及", "、", ",", "，", ";", "；")


@dataclass(frozen=True)
class SearchRouterResult:
    original_query: str
    normalized_query: str
    query_type: str
    routing_strategy: str
    decomposition_recommended: bool
    retrieval_mode: str
    language_signal_summary: str


@dataclass(frozen=True)
class SearchRouterDemoResult:
    router_result: SearchRouterResult
    query_received: str
    retrieval_mode_used: str
    top_k_returned: int
    search_router_layer_appears_successful: bool


class DeterministicSearchRouter:
    """Rule-based query classifier + routing decision layer."""

    def __init__(self) -> None:
        self.pt_mixed_normalizer = PortugueseMixedQueryNormalizer()

    def normalize_query(self, raw_query: str) -> str:
        return self.pt_mixed_normalizer.normalize_and_detect(raw_query).normalized_query

    def route(self, raw_query: str) -> SearchRouterResult:
        pt_signal = self.pt_mixed_normalizer.normalize_and_detect(raw_query)
        query_type = self._classify_query_type(pt_signal.normalized_query, pt_signal)
        return self._build_routing_result(
            raw_query=raw_query,
            normalized_query=pt_signal.normalized_query,
            query_type=query_type,
            language_signal_summary=pt_signal.language_signal_summary,
            pt_multi_issue=pt_signal.multi_issue_hint,
        )

    def _classify_query_type(self, query: str, pt_signal: PortugueseMixedNormalizationResult) -> str:
        lowered = query.lower()
        legal_count = self._keyword_count(query, LEGAL_CONCEPT_HINTS)
        fact_count = self._keyword_count(query, FACT_HINTS)
        connector_count = sum(query.count(token) for token in MULTI_ISSUE_CONNECTORS)

        if pt_signal.has_case_number and (pt_signal.pt_lexicon_hits or pt_signal.mixed_language):
            return "case_number_lookup_pt_mixed"
        if self._contains_case_number(query):
            return "case_number_lookup"
        if self._looks_portuguese_or_mixed(query, lowered, pt_signal):
            return "portuguese_or_mixed"
        if self._is_ambiguous_or_noisy(query):
            return "ambiguous_or_noisy"
        if pt_signal.multi_issue_hint and (pt_signal.mixed_language or pt_signal.pt_lexicon_hits):
            return "portuguese_or_mixed_multi_issue"
        if legal_count >= 1 and fact_count >= 1:
            return "mixed_fact_legal_query"
        if legal_count >= 2 or (legal_count >= 1 and connector_count >= 2):
            return "multi_issue_legal_query"
        if legal_count == 1:
            return "single_legal_concept"

        return "ambiguous_or_noisy"

    @staticmethod
    def _contains_case_number(query: str) -> bool:
        return bool(CASE_NUMBER_PATTERN.search(query))

    @staticmethod
    def _keyword_count(query: str, keywords: tuple[str, ...]) -> int:
        return sum(1 for keyword in keywords if keyword in query)

    @staticmethod
    def _looks_portuguese_or_mixed(
        query: str, lowered: str, pt_signal: PortugueseMixedNormalizationResult
    ) -> bool:
        ascii_letters = sum(1 for char in query if char.isascii() and char.isalpha())
        cjk_chars = sum(1 for char in query if "\u4e00" <= char <= "\u9fff")
        portuguese_hit = bool(pt_signal.pt_lexicon_hits)
        mixed_language = ascii_letters >= 6 and cjk_chars >= 2
        return portuguese_hit or mixed_language or pt_signal.mixed_language

    @staticmethod
    def _is_ambiguous_or_noisy(query: str) -> bool:
        if len(query) <= 2:
            return True

        alnum_or_cjk = [ch for ch in query if ch.isalnum() or ("\u4e00" <= ch <= "\u9fff")]
        if not alnum_or_cjk:
            return True

        noise_ratio = 1 - (len(alnum_or_cjk) / max(len(query), 1))
        if noise_ratio > 0.45:
            return True

        meaningless_tokens = {"help", "pls", "請問", "幫我", "看看", "?", "？？"}
        return query.lower() in meaningless_tokens

    @staticmethod
    def _build_routing_result(
        raw_query: str,
        normalized_query: str,
        query_type: str,
        language_signal_summary: str,
        pt_multi_issue: bool,
    ) -> SearchRouterResult:
        if query_type == "case_number_lookup_pt_mixed":
            return SearchRouterResult(
                original_query=raw_query,
                normalized_query=normalized_query,
                query_type=query_type,
                routing_strategy="exact_case_number_heavy_with_pt_context_retention",
                decomposition_recommended=False,
                retrieval_mode="exact_case_number_heavy_bm25_pt_context",
                language_signal_summary=language_signal_summary,
            )

        if query_type == "case_number_lookup":
            return SearchRouterResult(
                original_query=raw_query,
                normalized_query=normalized_query,
                query_type=query_type,
                routing_strategy="prefer_exact_case_number_path_then_hybrid_fallback",
                decomposition_recommended=False,
                retrieval_mode="exact_case_number_heavy_bm25",
                language_signal_summary=language_signal_summary,
            )

        if query_type == "single_legal_concept":
            return SearchRouterResult(
                original_query=raw_query,
                normalized_query=normalized_query,
                query_type=query_type,
                routing_strategy="direct_hybrid_skeleton_bm25_first",
                decomposition_recommended=False,
                retrieval_mode="direct_bm25_or_hybrid_skeleton",
                language_signal_summary=language_signal_summary,
            )

        if query_type == "multi_issue_legal_query":
            return SearchRouterResult(
                original_query=raw_query,
                normalized_query=normalized_query,
                query_type=query_type,
                routing_strategy="decomposition_aware_hybrid_retrieval",
                decomposition_recommended=True,
                retrieval_mode="decomposition_aware_bm25_hybrid",
                language_signal_summary=language_signal_summary,
            )

        if query_type == "mixed_fact_legal_query":
            return SearchRouterResult(
                original_query=raw_query,
                normalized_query=normalized_query,
                query_type=query_type,
                routing_strategy="decomposition_aware_hybrid_retrieval",
                decomposition_recommended=True,
                retrieval_mode="decomposition_aware_bm25_hybrid",
                language_signal_summary=language_signal_summary,
            )

        if query_type in {"portuguese_or_mixed", "portuguese_or_mixed_multi_issue"}:
            return SearchRouterResult(
                original_query=raw_query,
                normalized_query=normalized_query,
                query_type=query_type,
                routing_strategy="language_aware_bm25_path",
                decomposition_recommended=pt_multi_issue,
                retrieval_mode="bm25_language_aware_pt_or_mixed",
                language_signal_summary=language_signal_summary,
            )

        return SearchRouterResult(
            original_query=raw_query,
            normalized_query=normalized_query,
            query_type="ambiguous_or_noisy",
            routing_strategy="conservative_direct_retrieval",
            decomposition_recommended=False,
            retrieval_mode="conservative_direct_bm25",
            language_signal_summary=language_signal_summary,
        )


class LocalSearchRouterDemo:
    """Local demo: route query first, then call retrieval flow accordingly."""

    def __init__(self) -> None:
        self.router = DeterministicSearchRouter()
        self.direct_retriever = build_default_hybrid_retriever(enable_query_normalization=True)
        self.decomposition_retriever = DecompositionAwareHybridRetriever()

    def run(self, query: str, top_k: int = 5) -> SearchRouterDemoResult:
        router_result = self.router.route(query)

        retrieval_mode_used = router_result.retrieval_mode
        top_k_returned = 0
        appears_successful = False

        if router_result.decomposition_recommended:
            retrieval_result: DecompositionAwareRetrievalResult = self.decomposition_retriever.retrieve(
                query=router_result.normalized_query,
                top_k=top_k,
                decompose=True,
            )
            top_k_returned = retrieval_result.top_k_returned
            appears_successful = retrieval_result.decomposition_aware_retrieval_appears_successful
            retrieval_mode_used = f"{router_result.retrieval_mode}|decomposition_fanout"
        else:
            retrieval_result: HybridRetrievalResult = self.direct_retriever.retrieve(
                query=router_result.normalized_query,
                top_k=top_k,
            )
            top_k_returned = retrieval_result.top_k_returned
            appears_successful = retrieval_result.skeleton_successful
            retrieval_mode_used = f"{router_result.retrieval_mode}|direct"

        return SearchRouterDemoResult(
            router_result=router_result,
            query_received=query,
            retrieval_mode_used=retrieval_mode_used,
            top_k_returned=top_k_returned,
            search_router_layer_appears_successful=appears_successful,
        )


def write_demo_report(result: SearchRouterDemoResult, output_path: Path) -> None:
    lines = [
        "Search Router Layer Demo Report - Macau Court Cases",
        f"query received: {result.query_received}",
        f"normalized query: {result.router_result.normalized_query}",
        f"detected language signals: {result.router_result.language_signal_summary}",
        f"query_type: {result.router_result.query_type}",
        f"routing_strategy: {result.router_result.routing_strategy}",
        f"decomposition recommended: {result.router_result.decomposition_recommended}",
        f"retrieval mode used: {result.retrieval_mode_used}",
        f"top_k_returned: {result.top_k_returned}",
        (
            "whether search router layer appears successful: "
            f"{result.search_router_layer_appears_successful}"
        ),
        "router_result_json:",
        json.dumps(asdict(result.router_result), ensure_ascii=False, indent=2),
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local deterministic search router layer demo")
    parser.add_argument("--query", required=True, type=str, help="raw query string")
    parser.add_argument("--top_k", type=int, default=5, help="number of retrieval hits to request")
    parser.add_argument("--output", type=Path, default=DEMO_REPORT_PATH, help="path to local demo report")
    parser.add_argument("--json", action="store_true", help="print JSON result")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    demo = LocalSearchRouterDemo()
    result = demo.run(query=args.query, top_k=args.top_k)
    write_demo_report(result=result, output_path=args.output)

    print(f"query received: {result.query_received}")
    print(f"normalized query: {result.router_result.normalized_query}")
    print(f"detected language signals: {result.router_result.language_signal_summary}")
    print(f"query_type: {result.router_result.query_type}")
    print(f"routing_strategy: {result.router_result.routing_strategy}")
    print(f"decomposition recommended: {result.router_result.decomposition_recommended}")
    print(f"retrieval mode used: {result.retrieval_mode_used}")
    print(f"whether search router layer appears successful: {result.search_router_layer_appears_successful}")

    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
