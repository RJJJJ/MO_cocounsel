#!/usr/bin/env python3
"""Deterministic answer synthesis skeleton built on retrieval + citation binding.

Day 29 scope:
- local-only orchestration
- no database integration
- no external API calls
- no LLM integration
- no changes to retrieval/citation main flow

This module consumes hybrid retrieval hits and citation-ready records, then emits a
structured legal research draft that is explicitly retrieval-grounded and
provisional.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import sys

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from crawler.retrieval.citation_binding_layer import CitationBindingLayer, CitationRecord
from crawler.retrieval.hybrid_retrieval_skeleton import HybridRetrievalResult, build_default_hybrid_retriever

DEMO_REPORT_PATH = Path("data/eval/answer_synthesis_demo_report.txt")


@dataclass(frozen=True)
class StructuredFinding:
    finding_text: str
    citation_labels: list[str]


@dataclass(frozen=True)
class CitedSource:
    citation_label: str
    chunk_id: str
    pdf_url: str
    text_url_or_action: str


@dataclass(frozen=True)
class StructuredResearchDraft:
    query: str
    answer_type: str
    provisional_summary: str
    key_findings: list[StructuredFinding]
    cited_sources: list[CitedSource]
    source_notes: list[str] | None


def _clean_preview(preview: str, max_len: int = 180) -> str:
    compact = " ".join(preview.split())
    return compact if len(compact) <= max_len else compact[: max_len - 1].rstrip() + "…"


def _build_provisional_summary(query: str, citations: list[CitationRecord], retrieval_result: HybridRetrievalResult) -> str:
    if not citations:
        return (
            "[Draft | Retrieval-Grounded] No matching sources were retrieved for this query. "
            "This output is only a scaffold and not legal advice."
        )

    top_labels = ", ".join(record.citation_label for record in citations[:2])
    return (
        "[Draft | Retrieval-Grounded] This structured research draft is generated deterministically "
        f"from {len(retrieval_result.hits)} hybrid retrieval hits for query \"{query}\". "
        f"Initial support appears in top sources: {top_labels}. "
        "It summarizes retrieved excerpts only and is not final legal advice."
    )


def _build_key_findings(citations: list[CitationRecord]) -> list[StructuredFinding]:
    findings: list[StructuredFinding] = []

    for record in citations[:5]:
        snippet = _clean_preview(record.chunk_text_preview)
        finding_text = (
            f"Retrieved excerpt indicates: {snippet} "
            f"(court={record.court}, date={record.authoritative_decision_date}, rank={record.source_rank})."
        )
        findings.append(
            StructuredFinding(
                finding_text=finding_text,
                citation_labels=[record.citation_label],
            )
        )

    if len(findings) < 3 and citations:
        while len(findings) < 3:
            record = citations[-1]
            findings.append(
                StructuredFinding(
                    finding_text=(
                        "Additional supporting excerpt was reused due to limited unique hits; "
                        f"source preview: {_clean_preview(record.chunk_text_preview)}."
                    ),
                    citation_labels=[record.citation_label],
                )
            )

    return findings


def _build_cited_sources(citations: list[CitationRecord]) -> list[CitedSource]:
    seen_chunk_ids: set[str] = set()
    sources: list[CitedSource] = []

    for record in citations:
        if record.chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(record.chunk_id)
        sources.append(
            CitedSource(
                citation_label=record.citation_label,
                chunk_id=record.chunk_id,
                pdf_url=record.pdf_url,
                text_url_or_action=record.text_url_or_action,
            )
        )

    return sources


def generate_structured_draft(query: str, retrieval_result: HybridRetrievalResult, citations: list[CitationRecord]) -> StructuredResearchDraft:
    findings = _build_key_findings(citations)
    source_notes: list[str] | None = [
        "Deterministic synthesis only: no generative model was used.",
        "All findings are assembled from retrieval chunk previews and citation records.",
        "This draft is retrieval-grounded and should be reviewed by legal professionals before use.",
    ]
    if not citations:
        source_notes.append("No citations available; findings are placeholders for downstream handling.")

    return StructuredResearchDraft(
        query=query,
        answer_type="structured_research_draft",
        provisional_summary=_build_provisional_summary(query=query, citations=citations, retrieval_result=retrieval_result),
        key_findings=findings,
        cited_sources=_build_cited_sources(citations),
        source_notes=source_notes,
    )


def run_demo(query: str, top_k: int, disable_query_normalization: bool) -> tuple[HybridRetrievalResult, list[CitationRecord], StructuredResearchDraft]:
    retriever = build_default_hybrid_retriever(enable_query_normalization=not disable_query_normalization)
    retrieval_result = retriever.retrieve(query=query, top_k=top_k)

    binder = CitationBindingLayer()
    citations = binder.bind(retrieval_result.hits)

    draft = generate_structured_draft(query=query, retrieval_result=retrieval_result, citations=citations)
    return retrieval_result, citations, draft


def write_demo_report(
    query: str,
    retrieval_result: HybridRetrievalResult,
    citations: list[CitationRecord],
    draft: StructuredResearchDraft,
    output_path: Path,
) -> None:
    lines = [
        "Answer Synthesis Skeleton Demo Report - Macau Court Cases",
        f"query_received: {query}",
        f"retrieval_hits_used: {len(retrieval_result.hits)}",
        f"citation_records_used: {len(citations)}",
        f"answer_type: {draft.answer_type}",
        f"answer_synthesis_skeleton_appears_successful: {bool(draft.key_findings and draft.cited_sources)}",
        "answer_draft_generated:",
        f"  provisional_summary: {draft.provisional_summary}",
        "  key_findings:",
    ]

    for idx, finding in enumerate(draft.key_findings, start=1):
        lines.append(f"    [{idx}] {finding.finding_text}")
        lines.append(f"         citation_labels={', '.join(finding.citation_labels)}")

    lines.append("  cited_sources:")
    for idx, source in enumerate(draft.cited_sources, start=1):
        lines.extend(
            [
                f"    [{idx}] citation_label={source.citation_label}",
                f"         chunk_id={source.chunk_id}",
                f"         pdf_url={source.pdf_url}",
                f"         text_url_or_action={source.text_url_or_action}",
            ]
        )

    if draft.source_notes:
        lines.append("  source_notes:")
        for note in draft.source_notes:
            lines.append(f"    - {note}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local answer synthesis skeleton demo runner")
    parser.add_argument("query", type=str, help="query string")
    parser.add_argument("--top-k", type=int, default=5, help="top-k retrieval hits to synthesize")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEMO_REPORT_PATH,
        help="path to local answer synthesis demo report",
    )
    parser.add_argument(
        "--disable-query-normalization",
        action="store_true",
        help="disable query normalization hook used by hybrid retrieval",
    )
    parser.add_argument("--json", action="store_true", help="print synthesis draft as JSON")
    return parser.parse_args()


def _to_jsonable(draft: StructuredResearchDraft) -> dict[str, Any]:
    return asdict(draft)


def main() -> None:
    args = parse_args()
    retrieval_result, citations, draft = run_demo(
        query=args.query,
        top_k=args.top_k,
        disable_query_normalization=args.disable_query_normalization,
    )
    write_demo_report(
        query=args.query,
        retrieval_result=retrieval_result,
        citations=citations,
        draft=draft,
        output_path=args.output,
    )

    print(f"query received: {args.query}")
    print(f"retrieval hits used: {len(retrieval_result.hits)}")
    print(f"citation records used: {len(citations)}")
    print("answer draft generated: true")
    print(f"answer synthesis skeleton appears successful: {bool(draft.key_findings and draft.cited_sources)}")

    if args.json:
        print(json.dumps(_to_jsonable(draft), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
