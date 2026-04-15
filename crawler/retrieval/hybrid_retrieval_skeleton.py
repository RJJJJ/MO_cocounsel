#!/usr/bin/env python3
"""Hybrid retrieval skeleton (local-only) on top of BM25 baseline.

This module provides stable interfaces for future dense retrieval, fusion,
reranking, issue decomposition, and citation binding while keeping BM25 as the
only active retriever for Day 27.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from crawler.retrieval.improve_chinese_legal_query_normalization import (
    ChineseLegalQueryNormalizer,
    NormalizedQuery,
)
from crawler.retrieval.local_bm25_query_prototype import (
    BM25_CHUNKS_PATH,
    LocalBM25Index,
    MixedTokenizer,
    RankedHit,
    read_jsonl,
)

DEMO_REPORT_PATH = Path("data/eval/hybrid_retrieval_demo_report.txt")


@dataclass(frozen=True)
class RetrievalHit:
    """Citation-ready retrieval hit schema for hybrid pipelines."""

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


class QueryNormalizer(Protocol):
    def normalize(self, query: str) -> NormalizedQuery | None:
        """Normalize and optionally expand raw user query."""


class BM25Retriever(Protocol):
    def retrieve(self, query: str, top_k: int) -> list[RetrievalHit]:
        """Return top BM25 hits in the unified retrieval schema."""


class DenseRetrieverPlaceholder(Protocol):
    def retrieve(self, query: str, top_k: int) -> list[RetrievalHit]:
        """Placeholder for future dense retrieval outputs."""


class FusionStrategy(Protocol):
    def fuse(
        self,
        bm25_hits: list[RetrievalHit],
        dense_hits: list[RetrievalHit],
        top_k: int,
    ) -> list[RetrievalHit]:
        """Merge BM25 and dense hits into a final candidate list."""


class RerankHook(Protocol):
    def rerank(self, query: str, hits: list[RetrievalHit]) -> list[RetrievalHit]:
        """Placeholder hook for future reranking stage."""


class ChineseLegalQueryNormalizerHook:
    """Query normalization hook wrapping existing Day 26 normalizer."""

    def __init__(self) -> None:
        self._normalizer = ChineseLegalQueryNormalizer()

    def normalize(self, query: str) -> NormalizedQuery:
        return self._normalizer.normalize_query(query)


class LocalBM25Retriever:
    """BM25 retriever adapter to unified RetrievalHit schema."""

    def __init__(self, bm25_records: list[dict[str, Any]], tokenizer_mode: str = "deterministic") -> None:
        self._index = LocalBM25Index(records=bm25_records, tokenizer=MixedTokenizer(mode=tokenizer_mode))

    def retrieve(self, query: str, top_k: int) -> list[RetrievalHit]:
        hits, _, _ = self._index.search(query=query, top_k=top_k)
        return [self._to_retrieval_hit(hit) for hit in hits]

    @staticmethod
    def _to_retrieval_hit(hit: RankedHit) -> RetrievalHit:
        return RetrievalHit(
            chunk_id=hit.chunk_id,
            score=hit.score,
            retrieval_source="bm25",
            authoritative_case_number=hit.authoritative_case_number,
            authoritative_decision_date=hit.authoritative_decision_date,
            court=hit.court,
            language=hit.language,
            case_type=hit.case_type,
            chunk_text_preview=hit.chunk_text_preview,
            pdf_url=hit.pdf_url,
            text_url_or_action=hit.text_url_or_action,
        )


class LocalDenseRetrieverPlaceholder:
    """No-op dense retriever placeholder (intentionally inactive for Day 27)."""

    def retrieve(self, query: str, top_k: int) -> list[RetrievalHit]:
        _ = (query, top_k)
        return []


class BM25FirstFusionStrategy:
    """Simple merge strategy for skeleton stage.

    Current behavior: BM25-only pass-through.
    Future behavior: reciprocal rank fusion / weighted fusion.
    """

    def fuse(self, bm25_hits: list[RetrievalHit], dense_hits: list[RetrievalHit], top_k: int) -> list[RetrievalHit]:
        _ = dense_hits
        return bm25_hits[: max(top_k, 1)]


class IdentityRerankHook:
    """No-op rerank hook to keep flow and interface stable."""

    def rerank(self, query: str, hits: list[RetrievalHit]) -> list[RetrievalHit]:
        _ = query
        return hits


@dataclass(frozen=True)
class HybridRetrievalResult:
    query_received: str
    normalized_query: str
    top_k_requested: int
    top_k_returned: int
    retrieval_mode_used: str
    hits: list[RetrievalHit]
    skeleton_successful: bool


class HybridRetriever:
    """Flow orchestration layer for hybrid retrieval.

    Day 27 active path:
      query normalizer -> BM25 retriever -> fusion interface -> rerank hook

    Reserved interfaces:
      - dense retrieval output
      - fusion strategy plug-in
      - rerank hook plug-in
      - future issue decomposition and citation binder stages
    """

    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        dense_retriever: DenseRetrieverPlaceholder,
        fusion_strategy: FusionStrategy,
        rerank_hook: RerankHook,
        query_normalizer: QueryNormalizer | None = None,
    ) -> None:
        self.bm25_retriever = bm25_retriever
        self.dense_retriever = dense_retriever
        self.fusion_strategy = fusion_strategy
        self.rerank_hook = rerank_hook
        self.query_normalizer = query_normalizer

    def retrieve(self, query: str, top_k: int = 10) -> HybridRetrievalResult:
        normalized_query = query
        if self.query_normalizer is not None:
            normalized = self.query_normalizer.normalize(query)
            if normalized is not None:
                normalized_query = normalized.expanded_query

        bm25_hits = self.bm25_retriever.retrieve(query=normalized_query, top_k=top_k)
        dense_hits = self.dense_retriever.retrieve(query=normalized_query, top_k=top_k)

        fused_hits = self.fusion_strategy.fuse(bm25_hits=bm25_hits, dense_hits=dense_hits, top_k=top_k)
        reranked_hits = self.rerank_hook.rerank(query=normalized_query, hits=fused_hits)

        final_hits = reranked_hits[: max(top_k, 1)]
        return HybridRetrievalResult(
            query_received=query,
            normalized_query=normalized_query,
            top_k_requested=top_k,
            top_k_returned=len(final_hits),
            retrieval_mode_used="hybrid_skeleton_bm25_active_dense_placeholder",
            hits=final_hits,
            skeleton_successful=bool(final_hits),
        )


def write_demo_report(result: HybridRetrievalResult, output_path: Path) -> None:
    lines = [
        "Hybrid Retrieval Skeleton Demo Report - Macau Court Cases",
        f"bm25_input_path: {BM25_CHUNKS_PATH}",
        f"retrieval_mode_used: {result.retrieval_mode_used}",
        f"query_received: {result.query_received}",
        f"normalized_query: {result.normalized_query}",
        f"top_k_requested: {result.top_k_requested}",
        f"top_k_returned: {result.top_k_returned}",
        f"hybrid_retrieval_skeleton_appears_successful: {result.skeleton_successful}",
        "top_hits:",
    ]

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
            ]
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local hybrid retrieval skeleton runner (BM25 active)")
    parser.add_argument("query", type=str, help="query string")
    parser.add_argument("--top-k", type=int, default=5, help="number of top hits to return")
    parser.add_argument(
        "--disable-query-normalization",
        action="store_true",
        help="disable query normalization hook",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEMO_REPORT_PATH,
        help="path to local demo report",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="print JSON output for programmatic checks",
    )
    return parser.parse_args()


def build_default_hybrid_retriever(enable_query_normalization: bool = True) -> HybridRetriever:
    bm25_records = read_jsonl(BM25_CHUNKS_PATH)
    bm25_retriever = LocalBM25Retriever(bm25_records=bm25_records)
    dense_placeholder = LocalDenseRetrieverPlaceholder()
    fusion = BM25FirstFusionStrategy()
    reranker = IdentityRerankHook()
    normalizer = ChineseLegalQueryNormalizerHook() if enable_query_normalization else None

    return HybridRetriever(
        bm25_retriever=bm25_retriever,
        dense_retriever=dense_placeholder,
        fusion_strategy=fusion,
        rerank_hook=reranker,
        query_normalizer=normalizer,
    )


def main() -> None:
    args = parse_args()
    retriever = build_default_hybrid_retriever(enable_query_normalization=not args.disable_query_normalization)
    result = retriever.retrieve(query=args.query, top_k=args.top_k)
    write_demo_report(result=result, output_path=args.output)

    print(f"retrieval mode used: {result.retrieval_mode_used}")
    print(f"query received: {result.query_received}")
    print(f"top_k returned: {result.top_k_returned}")
    print(f"hybrid retrieval skeleton appears successful: {result.skeleton_successful}")

    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
