#!/usr/bin/env python3
"""Day 32 end-to-end local research pipeline integration demo.

Pipeline shape:
query -> issue decomposition -> hybrid retrieval -> citation binding -> answer synthesis

Constraints:
- local-only
- no database integration
- no external API calls
- no LLM integration
- orchestration/integration only (no module rewrites)
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

from crawler.retrieval.answer_synthesis_skeleton import generate_structured_draft
from crawler.retrieval.citation_binding_layer import CitationBindingLayer
from crawler.retrieval.hybrid_retrieval_skeleton import HybridRetrievalResult, RetrievalHit
from crawler.retrieval.hybrid_retrieval_with_decomposition import DecompositionAwareHybridRetriever
from crawler.retrieval.issue_decomposition_layer import RuleBasedIssueDecomposer

DEMO_REPORT_PATH = Path("data/eval/end_to_end_research_pipeline_demo_report.txt")


@dataclass(frozen=True)
class DecompositionSummary:
    main_issue: str
    sub_issues: list[str]
    retrieval_subqueries: list[str]


@dataclass(frozen=True)
class RetrievalSummary:
    hits_used: int
    top_case_numbers: list[str]


@dataclass(frozen=True)
class CitationSummary:
    citation_labels: list[str]
    source_count: int


@dataclass(frozen=True)
class EndToEndAnswerResult:
    query: str
    decomposition_summary: DecompositionSummary
    retrieval_summary: RetrievalSummary
    citation_summary: CitationSummary
    answer_draft: str


@dataclass(frozen=True)
class EndToEndPipelineResult:
    query_received: str
    decomposition_used: str
    subqueries_generated_count: int
    retrieval_hits_after_merge: int
    citation_records_generated: int
    answer_draft_generated: bool
    end_to_end_research_pipeline_appears_successful: bool
    answer_result: EndToEndAnswerResult


class EndToEndResearchPipelineDemo:
    """Local integration orchestrator for Day 32 acceptance demo."""

    def __init__(self) -> None:
        self._retriever = DecompositionAwareHybridRetriever()
        self._decomposer = RuleBasedIssueDecomposer()
        self._binder = CitationBindingLayer()

    def run(self, query: str, top_k: int = 5, decompose: bool = True) -> EndToEndPipelineResult:
        retrieval_result = self._retriever.retrieve(query=query, top_k=top_k, decompose=decompose)

        decomposition_summary = self._build_decomposition_summary(
            query=query,
            decompose=decompose,
            retrieval_subqueries=retrieval_result.retrieval_subqueries,
        )

        hits_for_binding = [self._to_retrieval_hit(hit) for hit in retrieval_result.hits]
        citations = self._binder.bind(hits_for_binding)

        synthesis_input = HybridRetrievalResult(
            query_received=query,
            normalized_query=query,
            top_k_requested=top_k,
            top_k_returned=len(hits_for_binding),
            retrieval_mode_used="day32_end_to_end_pipeline_local_demo",
            hits=hits_for_binding,
            skeleton_successful=bool(hits_for_binding),
        )
        draft = generate_structured_draft(query=query, retrieval_result=synthesis_input, citations=citations)

        retrieval_summary = RetrievalSummary(
            hits_used=len(hits_for_binding),
            top_case_numbers=self._extract_top_case_numbers(hits_for_binding),
        )
        citation_summary = CitationSummary(
            citation_labels=[record.citation_label for record in citations],
            source_count=len(citations),
        )

        answer_result = EndToEndAnswerResult(
            query=query,
            decomposition_summary=decomposition_summary,
            retrieval_summary=retrieval_summary,
            citation_summary=citation_summary,
            answer_draft=draft.provisional_summary,
        )

        appears_successful = bool(hits_for_binding and citations and draft.provisional_summary.strip())

        return EndToEndPipelineResult(
            query_received=query,
            decomposition_used="on" if decompose else "off",
            subqueries_generated_count=retrieval_result.subqueries_generated_count,
            retrieval_hits_after_merge=retrieval_result.retrieval_hits_after_merge,
            citation_records_generated=len(citations),
            answer_draft_generated=bool(draft.provisional_summary.strip()),
            end_to_end_research_pipeline_appears_successful=appears_successful,
            answer_result=answer_result,
        )

    def _build_decomposition_summary(
        self,
        query: str,
        decompose: bool,
        retrieval_subqueries: list[str],
    ) -> DecompositionSummary:
        if decompose:
            decomposition = self._decomposer.decompose(query)
            return DecompositionSummary(
                main_issue=decomposition.main_issue,
                sub_issues=decomposition.sub_issues,
                retrieval_subqueries=retrieval_subqueries,
            )

        normalized = query.strip()
        return DecompositionSummary(
            main_issue=normalized,
            sub_issues=[],
            retrieval_subqueries=retrieval_subqueries,
        )

    @staticmethod
    def _to_retrieval_hit(hit: object) -> RetrievalHit:
        return RetrievalHit(
            chunk_id=getattr(hit, "chunk_id"),
            score=getattr(hit, "score"),
            retrieval_source=getattr(hit, "retrieval_source"),
            authoritative_case_number=getattr(hit, "authoritative_case_number"),
            authoritative_decision_date=getattr(hit, "authoritative_decision_date"),
            court=getattr(hit, "court"),
            language=getattr(hit, "language"),
            case_type=getattr(hit, "case_type"),
            chunk_text_preview=getattr(hit, "chunk_text_preview"),
            pdf_url=getattr(hit, "pdf_url"),
            text_url_or_action=getattr(hit, "text_url_or_action"),
        )

    @staticmethod
    def _extract_top_case_numbers(hits: list[RetrievalHit], limit: int = 5) -> list[str]:
        seen: set[str] = set()
        case_numbers: list[str] = []
        for hit in hits:
            case_number = hit.authoritative_case_number.strip()
            if not case_number or case_number in seen:
                continue
            seen.add(case_number)
            case_numbers.append(case_number)
            if len(case_numbers) >= max(limit, 1):
                break
        return case_numbers


def write_demo_report(result: EndToEndPipelineResult, output_path: Path) -> None:
    lines = [
        "End-to-End Research Pipeline Demo Report - Day 32",
        f"query_received: {result.query_received}",
        f"decomposition_used: {result.decomposition_used}",
        f"subqueries_generated_count: {result.subqueries_generated_count}",
        f"retrieval_hits_after_merge: {result.retrieval_hits_after_merge}",
        f"citation_records_generated: {result.citation_records_generated}",
        f"answer_draft_generated: {result.answer_draft_generated}",
        (
            "end_to_end_research_pipeline_appears_successful: "
            f"{result.end_to_end_research_pipeline_appears_successful}"
        ),
        "",
        "answer_result:",
        json.dumps(asdict(result.answer_result), ensure_ascii=False, indent=2),
    ]
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local end-to-end research pipeline demo runner")
    parser.add_argument("--query", required=True, type=str, help="raw legal research query")
    parser.add_argument("--top_k", type=int, default=5, help="top-k merged hits for downstream stages")
    parser.add_argument(
        "--decompose",
        choices=["on", "off"],
        default="on",
        help="toggle issue decomposition before retrieval",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEMO_REPORT_PATH,
        help="path to local end-to-end pipeline report",
    )
    parser.add_argument("--json", action="store_true", help="print full JSON result")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    pipeline = EndToEndResearchPipelineDemo()
    result = pipeline.run(query=args.query, top_k=args.top_k, decompose=(args.decompose == "on"))

    write_demo_report(result=result, output_path=args.output)

    print(f"query received: {result.query_received}")
    print(f"decomposition used: {result.decomposition_used}")
    print(f"subqueries generated count: {result.subqueries_generated_count}")
    print(f"retrieval hits after merge: {result.retrieval_hits_after_merge}")
    print(f"citation records generated: {result.citation_records_generated}")
    print(f"answer draft generated: {result.answer_draft_generated}")
    print(
        "end-to-end research pipeline appears successful: "
        f"{result.end_to_end_research_pipeline_appears_successful}"
    )

    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
