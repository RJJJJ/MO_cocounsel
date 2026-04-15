#!/usr/bin/env python3
"""Deterministic structured research output synthesis built on retrieval + citation binding.

Day 33 scope:
- local-only orchestration
- no database integration
- no external API calls
- no LLM integration
- no changes to retrieval/citation main flow

This module consumes issue decomposition output, hybrid retrieval hits, and citation-ready
records, then emits a product-oriented structured legal research output that is
explicitly retrieval-grounded and provisional.
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
from crawler.retrieval.issue_decomposition_layer import IssueDecompositionResult, RuleBasedIssueDecomposer

DEMO_REPORT_PATH = Path("data/eval/structured_research_output_demo_report.txt")


@dataclass(frozen=True)
class StructuredFinding:
    finding_text: str
    citation_labels: list[str]


@dataclass(frozen=True)
class SupportingSource:
    citation_label: str
    chunk_id: str
    authoritative_case_number: str
    authoritative_decision_date: str
    court: str
    language: str
    case_type: str
    retrieval_source: str
    score: float
    pdf_url: str
    text_url_or_action: str


@dataclass(frozen=True)
class RetrievalOverview:
    hits_used: int
    citation_count: int
    top_case_numbers: list[str]


@dataclass(frozen=True)
class StructuredResearchOutput:
    query: str
    answer_type: str
    research_scope: str
    main_issue: str
    sub_issues: list[str]
    retrieval_overview: RetrievalOverview
    preliminary_findings: list[StructuredFinding]
    supporting_sources: list[SupportingSource]
    coverage_notes: list[str]
    limitations: list[str]
    next_actions: list[str]

    @property
    def provisional_summary(self) -> str:
        """Backward-compatible summary used by Day 32 pipeline wrapper."""
        return self.research_scope


def _clean_preview(preview: str, max_len: int = 180) -> str:
    compact = " ".join(preview.split())
    return compact if len(compact) <= max_len else compact[: max_len - 1].rstrip() + "…"


def _extract_top_case_numbers(citations: list[CitationRecord], limit: int = 5) -> list[str]:
    seen: set[str] = set()
    case_numbers: list[str] = []

    for record in citations:
        case_number = record.authoritative_case_number.strip()
        if not case_number or case_number in seen:
            continue
        seen.add(case_number)
        case_numbers.append(case_number)
        if len(case_numbers) >= max(limit, 1):
            break

    return case_numbers


def _build_research_scope(query: str, retrieval_result: HybridRetrievalResult, citations: list[CitationRecord]) -> str:
    return (
        "Local deterministic legal retrieval pass over prepared Macau court chunks; "
        f'query="{query}", hits={len(retrieval_result.hits)}, citations={len(citations)}. '
        "Findings are assembled from bound citation previews only."
    )


def _build_preliminary_findings(citations: list[CitationRecord]) -> list[StructuredFinding]:
    findings: list[StructuredFinding] = []

    for record in citations[:5]:
        snippet = _clean_preview(record.chunk_text_preview)
        finding_text = (
            f"Retrieved excerpt suggests: {snippet} "
            f"(court={record.court}, date={record.authoritative_decision_date}, rank={record.source_rank})."
        )
        findings.append(
            StructuredFinding(
                finding_text=finding_text,
                citation_labels=[record.citation_label],
            )
        )

    if not findings:
        findings.append(
            StructuredFinding(
                finding_text=(
                    "No preliminary finding could be grounded because no citation record was produced "
                    "for the current query."
                ),
                citation_labels=[],
            )
        )

    while len(findings) < 3:
        record = citations[-1]
        findings.append(
            StructuredFinding(
                finding_text=(
                    "Additional supporting excerpt reused due to limited unique hits; "
                    f"source preview: {_clean_preview(record.chunk_text_preview)}."
                ),
                citation_labels=[record.citation_label],
            )
        )

    return findings[:5]


def _build_supporting_sources(citations: list[CitationRecord]) -> list[SupportingSource]:
    seen_chunk_ids: set[str] = set()
    sources: list[SupportingSource] = []

    for record in citations:
        if record.chunk_id in seen_chunk_ids:
            continue
        seen_chunk_ids.add(record.chunk_id)
        sources.append(
            SupportingSource(
                citation_label=record.citation_label,
                chunk_id=record.chunk_id,
                authoritative_case_number=record.authoritative_case_number,
                authoritative_decision_date=record.authoritative_decision_date,
                court=record.court,
                language=record.language,
                case_type=record.case_type,
                retrieval_source=record.retrieval_source,
                score=record.score,
                pdf_url=record.pdf_url,
                text_url_or_action=record.text_url_or_action,
            )
        )

    return sources


def generate_structured_draft(
    query: str,
    retrieval_result: HybridRetrievalResult,
    citations: list[CitationRecord],
    decomposition_result: IssueDecompositionResult | None = None,
) -> StructuredResearchOutput:
    if decomposition_result is None:
        decomposition_result = RuleBasedIssueDecomposer().decompose(query)

    findings = _build_preliminary_findings(citations)
    supporting_sources = _build_supporting_sources(citations)

    return StructuredResearchOutput(
        query=query,
        answer_type="structured_research_output",
        research_scope=_build_research_scope(query=query, retrieval_result=retrieval_result, citations=citations),
        main_issue=decomposition_result.main_issue,
        sub_issues=decomposition_result.sub_issues,
        retrieval_overview=RetrievalOverview(
            hits_used=len(retrieval_result.hits),
            citation_count=len(citations),
            top_case_numbers=_extract_top_case_numbers(citations),
        ),
        preliminary_findings=findings,
        supporting_sources=supporting_sources,
        coverage_notes=[
            "This is a retrieval-grounded preliminary research output generated deterministically.",
            "Each preliminary finding is attached to citation labels from citation binding records.",
            "Output should be treated as an initial research artifact for analyst/legal review.",
        ],
        limitations=[
            "No dense retrieval is enabled in the current local pipeline.",
            "No LLM-based legal reasoning or narrative synthesis is performed.",
            "Coverage can be limited by corpus scope, query phrasing, and sparse retrieval recall.",
        ],
        next_actions=[
            "Validate whether additional issue-specific subqueries should be added before retrieval.",
            "Cross-check top cited cases against full-text holdings for doctrinal consistency.",
            "Evaluate adding a local dense retrieval stub or search router in the next iteration.",
        ],
    )


def run_demo(
    query: str,
    top_k: int,
    disable_query_normalization: bool,
) -> tuple[IssueDecompositionResult, HybridRetrievalResult, list[CitationRecord], StructuredResearchOutput]:
    decomposition_result = RuleBasedIssueDecomposer().decompose(query)

    retriever = build_default_hybrid_retriever(enable_query_normalization=not disable_query_normalization)
    retrieval_result = retriever.retrieve(query=query, top_k=top_k)

    binder = CitationBindingLayer()
    citations = binder.bind(retrieval_result.hits)

    draft = generate_structured_draft(
        query=query,
        retrieval_result=retrieval_result,
        citations=citations,
        decomposition_result=decomposition_result,
    )
    return decomposition_result, retrieval_result, citations, draft


def write_demo_report(
    query: str,
    decomposition_result: IssueDecompositionResult,
    retrieval_result: HybridRetrievalResult,
    citations: list[CitationRecord],
    draft: StructuredResearchOutput,
    output_path: Path,
) -> None:
    lines = [
        "Structured Research Output Demo Report - Macau Court Cases",
        f"query_received: {query}",
        f"main_issue: {decomposition_result.main_issue}",
        f"sub_issues_count: {len(decomposition_result.sub_issues)}",
        f"answer_type: {draft.answer_type}",
        f"retrieval_hits_used: {draft.retrieval_overview.hits_used}",
        f"citation_count: {draft.retrieval_overview.citation_count}",
        f"findings_count: {len(draft.preliminary_findings)}",
        f"supporting_sources_count: {len(draft.supporting_sources)}",
        (
            "structured_research_output_refinement_appears_successful: "
            f"{bool(draft.preliminary_findings and draft.supporting_sources and draft.main_issue)}"
        ),
        "answer_output_generated:",
        f"  research_scope: {draft.research_scope}",
        f"  top_case_numbers: {', '.join(draft.retrieval_overview.top_case_numbers)}",
        "  preliminary_findings:",
    ]

    for idx, finding in enumerate(draft.preliminary_findings, start=1):
        labels = ", ".join(finding.citation_labels) if finding.citation_labels else "(none)"
        lines.append(f"    [{idx}] {finding.finding_text}")
        lines.append(f"         citation_labels={labels}")

    lines.append("  supporting_sources:")
    for idx, source in enumerate(draft.supporting_sources, start=1):
        lines.extend(
            [
                f"    [{idx}] citation_label={source.citation_label}",
                f"         chunk_id={source.chunk_id}",
                f"         case_number={source.authoritative_case_number}",
                f"         decision_date={source.authoritative_decision_date}",
                f"         court={source.court}",
                f"         retrieval_source={source.retrieval_source}",
                f"         score={source.score:.6f}",
                f"         pdf_url={source.pdf_url}",
                f"         text_url_or_action={source.text_url_or_action}",
            ]
        )

    lines.append("  coverage_notes:")
    for note in draft.coverage_notes:
        lines.append(f"    - {note}")

    lines.append("  limitations:")
    for limitation in draft.limitations:
        lines.append(f"    - {limitation}")

    lines.append("  next_actions:")
    for action in draft.next_actions:
        lines.append(f"    - {action}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local structured research output demo runner")
    parser.add_argument("query", type=str, help="query string")
    parser.add_argument("--top-k", type=int, default=5, help="top-k retrieval hits to synthesize")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEMO_REPORT_PATH,
        help="path to local structured research output demo report",
    )
    parser.add_argument(
        "--disable-query-normalization",
        action="store_true",
        help="disable query normalization hook used by hybrid retrieval",
    )
    parser.add_argument("--json", action="store_true", help="print structured output as JSON")
    return parser.parse_args()


def _to_jsonable(draft: StructuredResearchOutput) -> dict[str, Any]:
    return asdict(draft)


def main() -> None:
    args = parse_args()
    decomposition_result, retrieval_result, citations, draft = run_demo(
        query=args.query,
        top_k=args.top_k,
        disable_query_normalization=args.disable_query_normalization,
    )
    write_demo_report(
        query=args.query,
        decomposition_result=decomposition_result,
        retrieval_result=retrieval_result,
        citations=citations,
        draft=draft,
        output_path=args.output,
    )

    print(f"query received: {args.query}")
    print("answer output generated: true")
    print(f"findings count: {len(draft.preliminary_findings)}")
    print(f"supporting sources count: {len(draft.supporting_sources)}")
    print(
        "structured research output refinement appears successful: "
        f"{bool(draft.preliminary_findings and draft.supporting_sources and draft.main_issue)}"
    )

    if args.json:
        print(json.dumps(_to_jsonable(draft), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
