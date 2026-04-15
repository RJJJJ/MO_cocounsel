#!/usr/bin/env python3
"""Local citation binding layer for hybrid retrieval outputs.

Day 28 scope:
- local-only transformation
- no database integration
- no external API calls
- no changes to hybrid retrieval main flow

This module converts retrieval hits to citation-ready records that downstream
answer assembly can render directly as citation cards or inline references.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from crawler.retrieval.hybrid_retrieval_skeleton import (
    HybridRetrievalResult,
    RetrievalHit,
    build_default_hybrid_retriever,
)

DEMO_REPORT_PATH = Path("data/eval/citation_binding_demo_report.txt")


@dataclass(frozen=True)
class CitationRecord:
    """Citation-ready normalized record for downstream answer assembly."""

    chunk_id: str
    citation_label: str
    authoritative_case_number: str
    authoritative_decision_date: str
    court: str
    language: str
    case_type: str
    pdf_url: str
    text_url_or_action: str
    chunk_text_preview: str
    retrieval_source: str
    score: float
    source_rank: int
    source_group_key: str


class CitationBindingLayer:
    """Bind retrieval hits into deterministic citation-ready records."""

    def bind(self, hits: Iterable[RetrievalHit]) -> list[CitationRecord]:
        citation_records: list[CitationRecord] = []

        for rank, hit in enumerate(hits, start=1):
            citation_records.append(
                CitationRecord(
                    chunk_id=hit.chunk_id,
                    citation_label=self._build_citation_label(hit),
                    authoritative_case_number=hit.authoritative_case_number,
                    authoritative_decision_date=hit.authoritative_decision_date,
                    court=hit.court,
                    language=hit.language,
                    case_type=hit.case_type,
                    pdf_url=hit.pdf_url,
                    text_url_or_action=hit.text_url_or_action,
                    chunk_text_preview=hit.chunk_text_preview,
                    retrieval_source=hit.retrieval_source,
                    score=hit.score,
                    source_rank=rank,
                    source_group_key=self._build_source_group_key(hit),
                )
            )

        return citation_records

    @staticmethod
    def _normalize_label_part(value: str, fallback: str = "unknown") -> str:
        normalized = value.strip()
        return normalized if normalized else fallback

    def _build_citation_label(self, hit: RetrievalHit) -> str:
        court = self._normalize_label_part(hit.court)
        case_number = self._normalize_label_part(hit.authoritative_case_number)
        decision_date = self._normalize_label_part(hit.authoritative_decision_date)
        return f"{court}｜{case_number}｜{decision_date}"

    def _build_source_group_key(self, hit: RetrievalHit) -> str:
        court = self._normalize_label_part(hit.court)
        case_number = self._normalize_label_part(hit.authoritative_case_number)
        decision_date = self._normalize_label_part(hit.authoritative_decision_date)
        retrieval_source = self._normalize_label_part(hit.retrieval_source)
        return f"{court}::{case_number}::{decision_date}::{retrieval_source}"


def write_demo_report(
    query: str,
    retrieval_result: HybridRetrievalResult,
    citations: list[CitationRecord],
    output_path: Path,
) -> None:
    lines = [
        "Citation Binding Layer Demo Report - Macau Court Cases",
        f"query_received: {query}",
        f"retrieval_hits_received: {len(retrieval_result.hits)}",
        f"citation_records_generated: {len(citations)}",
        f"citation_binding_layer_appears_successful: {bool(citations)}",
        "citation_records:",
    ]

    for record in citations:
        lines.extend(
            [
                f"  [{record.source_rank}] citation_label={record.citation_label}",
                f"       chunk_id={record.chunk_id}",
                f"       authoritative_case_number={record.authoritative_case_number}",
                f"       authoritative_decision_date={record.authoritative_decision_date}",
                f"       court={record.court}",
                f"       language={record.language}",
                f"       case_type={record.case_type}",
                f"       pdf_url={record.pdf_url}",
                f"       text_url_or_action={record.text_url_or_action}",
                f"       chunk_text_preview={record.chunk_text_preview}",
                f"       retrieval_source={record.retrieval_source}",
                f"       score={record.score:.6f}",
                f"       source_group_key={record.source_group_key}",
            ]
        )

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local citation binding layer demo runner")
    parser.add_argument("query", type=str, help="query string")
    parser.add_argument("--top-k", type=int, default=5, help="top-k retrieval hits to bind")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEMO_REPORT_PATH,
        help="path to local citation binding demo report",
    )
    parser.add_argument(
        "--disable-query-normalization",
        action="store_true",
        help="disable query normalization hook used by hybrid retrieval",
    )
    parser.add_argument("--json", action="store_true", help="print citation records as JSON")
    return parser.parse_args()


def _to_jsonable(records: list[CitationRecord]) -> list[dict[str, Any]]:
    return [asdict(item) for item in records]


def run_demo(query: str, top_k: int, disable_query_normalization: bool) -> tuple[HybridRetrievalResult, list[CitationRecord]]:
    retriever = build_default_hybrid_retriever(enable_query_normalization=not disable_query_normalization)
    retrieval_result = retriever.retrieve(query=query, top_k=top_k)

    binder = CitationBindingLayer()
    citations = binder.bind(retrieval_result.hits)
    return retrieval_result, citations


def main() -> None:
    args = parse_args()
    retrieval_result, citations = run_demo(
        query=args.query,
        top_k=args.top_k,
        disable_query_normalization=args.disable_query_normalization,
    )
    write_demo_report(
        query=args.query,
        retrieval_result=retrieval_result,
        citations=citations,
        output_path=args.output,
    )

    print(f"query received: {args.query}")
    print(f"retrieval hits received: {len(retrieval_result.hits)}")
    print(f"citation records generated: {len(citations)}")
    print(f"citation binding layer appears successful: {bool(citations)}")

    if args.json:
        import json

        print(json.dumps(_to_jsonable(citations), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
