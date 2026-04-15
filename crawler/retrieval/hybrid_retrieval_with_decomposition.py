#!/usr/bin/env python3
"""Decomposition-aware hybrid retrieval orchestration (local-only).

Day 31 scope:
- integrate local issue decomposition as optional pre-retrieval stage
- fan out retrieval subqueries to existing hybrid retrieval skeleton (BM25-active)
- merge and dedupe hits deterministically by chunk_id
- no database integration
- no external API calls
- no dense retrieval activation
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

from crawler.retrieval.hybrid_retrieval_skeleton import RetrievalHit, build_default_hybrid_retriever
from crawler.retrieval.issue_decomposition_layer import RuleBasedIssueDecomposer

DEMO_REPORT_PATH = Path("data/eval/hybrid_retrieval_with_decomposition_demo_report.txt")


@dataclass(frozen=True)
class MergedRetrievalHit:
    chunk_id: str
    score: float
    retrieval_source: str
    authoritative_case_number: str
    authoritative_decision_date: str
    court: str
    language: str
    case_type: str
    chunk_text_preview: str
    pdf_url: str
    text_url_or_action: str
    matched_subqueries: list[str]


@dataclass(frozen=True)
class DecompositionAwareRetrievalResult:
    query_received: str
    decomposition_used: str
    subqueries_generated_count: int
    retrieval_hits_before_merge: int
    retrieval_hits_after_merge: int
    top_k_requested: int
    top_k_returned: int
    decomposition_aware_retrieval_appears_successful: bool
    retrieval_subqueries: list[str]
    hits: list[MergedRetrievalHit]


class DecompositionAwareHybridRetriever:
    """Optional issue decomposition + hybrid retrieval fan-out orchestrator."""

    def __init__(self) -> None:
        self._hybrid = build_default_hybrid_retriever(enable_query_normalization=True)
        self._decomposer = RuleBasedIssueDecomposer()

    def retrieve(self, query: str, top_k: int = 5, decompose: bool = True) -> DecompositionAwareRetrievalResult:
        retrieval_subqueries = self._build_subqueries(query=query, decompose=decompose)

        all_hits: list[tuple[str, RetrievalHit]] = []
        for subquery in retrieval_subqueries:
            subquery_result = self._hybrid.retrieve(query=subquery, top_k=top_k)
            all_hits.extend((subquery, hit) for hit in subquery_result.hits)

        merged_hits = self._merge_and_dedupe_hits(all_hits)
        final_hits = merged_hits[: max(top_k, 1)]

        return DecompositionAwareRetrievalResult(
            query_received=query,
            decomposition_used="on" if decompose else "off",
            subqueries_generated_count=len(retrieval_subqueries),
            retrieval_hits_before_merge=len(all_hits),
            retrieval_hits_after_merge=len(merged_hits),
            top_k_requested=top_k,
            top_k_returned=len(final_hits),
            decomposition_aware_retrieval_appears_successful=bool(final_hits),
            retrieval_subqueries=retrieval_subqueries,
            hits=final_hits,
        )

    def _build_subqueries(self, query: str, decompose: bool) -> list[str]:
        if not decompose:
            return [query.strip()]

        decomposition = self._decomposer.decompose(query)
        candidates = [item.strip() for item in decomposition.retrieval_subqueries if item.strip()]

        # Keep stable order and uniqueness to guarantee deterministic fan-out.
        seen: set[str] = set()
        subqueries: list[str] = []
        for candidate in candidates:
            if candidate in seen:
                continue
            seen.add(candidate)
            subqueries.append(candidate)

        if not subqueries:
            return [query.strip()]
        return subqueries

    @staticmethod
    def _merge_and_dedupe_hits(all_hits: list[tuple[str, RetrievalHit]]) -> list[MergedRetrievalHit]:
        merged: dict[str, MergedRetrievalHit] = {}

        for subquery, hit in all_hits:
            existing = merged.get(hit.chunk_id)
            if existing is None:
                merged[hit.chunk_id] = MergedRetrievalHit(
                    chunk_id=hit.chunk_id,
                    score=hit.score,
                    retrieval_source=hit.retrieval_source,
                    authoritative_case_number=hit.authoritative_case_number,
                    authoritative_decision_date=hit.authoritative_decision_date,
                    court=hit.court,
                    language=hit.language,
                    case_type=hit.case_type,
                    chunk_text_preview=hit.chunk_text_preview,
                    pdf_url=hit.pdf_url,
                    text_url_or_action=hit.text_url_or_action,
                    matched_subqueries=[subquery],
                )
                continue

            best_score = existing.score
            if hit.score > existing.score:
                best_score = hit.score

            matched_subqueries = existing.matched_subqueries.copy()
            if subquery not in matched_subqueries:
                matched_subqueries.append(subquery)

            merged[hit.chunk_id] = MergedRetrievalHit(
                chunk_id=existing.chunk_id,
                score=best_score,
                retrieval_source=existing.retrieval_source,
                authoritative_case_number=existing.authoritative_case_number,
                authoritative_decision_date=existing.authoritative_decision_date,
                court=existing.court,
                language=existing.language,
                case_type=existing.case_type,
                chunk_text_preview=existing.chunk_text_preview,
                pdf_url=existing.pdf_url,
                text_url_or_action=existing.text_url_or_action,
                matched_subqueries=matched_subqueries,
            )

        return sorted(merged.values(), key=lambda item: (-item.score, item.chunk_id))


def write_demo_report(result: DecompositionAwareRetrievalResult, output_path: Path) -> None:
    lines = [
        "Hybrid Retrieval With Decomposition Demo Report - Macau Court Cases",
        f"query_received: {result.query_received}",
        f"decomposition_used: {result.decomposition_used}",
        f"subqueries_generated_count: {result.subqueries_generated_count}",
        f"retrieval_hits_before_merge: {result.retrieval_hits_before_merge}",
        f"retrieval_hits_after_merge: {result.retrieval_hits_after_merge}",
        f"top_k_requested: {result.top_k_requested}",
        f"top_k_returned: {result.top_k_returned}",
        (
            "decomposition_aware_retrieval_appears_successful: "
            f"{result.decomposition_aware_retrieval_appears_successful}"
        ),
        "retrieval_subqueries:",
    ]

    for idx, subquery in enumerate(result.retrieval_subqueries, start=1):
        lines.append(f"  [{idx}] {subquery}")

    lines.append("top_hits:")
    for rank, hit in enumerate(result.hits, start=1):
        lines.extend(
            [
                f"  [{rank}] score={hit.score:.6f}",
                f"       chunk_id={hit.chunk_id}",
                f"       retrieval_source={hit.retrieval_source}",
                f"       authoritative_case_number={hit.authoritative_case_number}",
                f"       authoritative_decision_date={hit.authoritative_decision_date}",
                f"       court={hit.court}",
                f"       language={hit.language}",
                f"       case_type={hit.case_type}",
                f"       chunk_text_preview={hit.chunk_text_preview}",
                f"       pdf_url={hit.pdf_url}",
                f"       text_url_or_action={hit.text_url_or_action}",
                f"       matched_subqueries={'; '.join(hit.matched_subqueries)}",
            ]
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local decomposition-aware hybrid retrieval runner")
    parser.add_argument("--query", required=True, type=str, help="raw query string")
    parser.add_argument("--top_k", type=int, default=5, help="number of top merged hits to return")
    parser.add_argument(
        "--decompose",
        choices=["on", "off"],
        default="on",
        help="toggle issue decomposition before retrieval fan-out",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEMO_REPORT_PATH,
        help="path to local decomposition-aware retrieval demo report",
    )
    parser.add_argument("--json", action="store_true", help="print JSON output")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    retriever = DecompositionAwareHybridRetriever()
    result = retriever.retrieve(query=args.query, top_k=args.top_k, decompose=(args.decompose == "on"))
    write_demo_report(result=result, output_path=args.output)

    print(f"query received: {result.query_received}")
    print(f"decomposition used: {result.decomposition_used}")
    print(f"subqueries generated count: {result.subqueries_generated_count}")
    print(f"retrieval hits before merge: {result.retrieval_hits_before_merge}")
    print(f"retrieval hits after merge: {result.retrieval_hits_after_merge}")
    print(f"top_k returned: {result.top_k_returned}")
    print(
        "decomposition-aware retrieval appears successful: "
        f"{result.decomposition_aware_retrieval_appears_successful}"
    )

    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
