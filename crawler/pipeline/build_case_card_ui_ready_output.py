#!/usr/bin/env python3
"""Day 51: build case-card / UI-ready output layer over metadata-integrated pipeline.

Flow:
query -> existing metadata-integrated research pipeline -> UI-ready case cards

Scope constraints:
- local-only
- no database integration
- no external API calls
- no cloud model calls
- output shaping only (no frontend rendering)
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

from crawler.pipeline.integrate_metadata_into_research_pipeline import (
    DEFAULT_BASELINE_METADATA_PATH,
    DEFAULT_MODEL_METADATA_PATH,
    MetadataIntegratedResearchPipeline,
)
from crawler.retrieval.hybrid_retrieval_with_decomposition import DecompositionAwareHybridRetriever

DEFAULT_REPORT_PATH = Path("data/eval/case_card_ui_ready_output_report.txt")


@dataclass(frozen=True)
class CaseCardUIReadyRecord:
    authoritative_case_number: str
    authoritative_decision_date: str
    court: str
    language: str
    case_type: str
    case_summary: str
    holding: str
    legal_basis: list[str]
    disputed_issues: list[str]
    metadata_source: str
    pdf_url: str
    text_url_or_action: str
    card_title: str
    card_subtitle: str
    card_tags: list[str]


@dataclass(frozen=True)
class CaseCardUIReadyOutput:
    query_received: str
    retrieved_cases_count: int
    case_cards_built: int
    model_generated_metadata_used_count: int
    deterministic_fallback_used_count: int
    case_card_ui_ready_output_appears_successful: bool
    case_cards: list[CaseCardUIReadyRecord]


def _build_case_number_to_date_map(query: str, top_k: int) -> dict[str, str]:
    retriever = DecompositionAwareHybridRetriever()
    retrieval_result = retriever.retrieve(query=query, top_k=top_k, decompose=True)

    mapping: dict[str, str] = {}
    for hit in retrieval_result.hits:
        case_number = hit.authoritative_case_number.strip()
        if not case_number or case_number in mapping:
            continue
        mapping[case_number] = hit.authoritative_decision_date.strip()
    return mapping


def _build_card_title(case_number: str, case_type: str, court: str) -> str:
    components = [part for part in [case_number, case_type, court] if part]
    return "｜".join(components) if components else "未命名案例"


def _build_card_subtitle(language: str, decision_date: str, metadata_source: str) -> str:
    language_part = language or "unknown-language"
    date_part = decision_date or "unknown-date"
    source_part = f"metadata:{metadata_source}" if metadata_source else "metadata:unknown"
    return f"{language_part} · {date_part} · {source_part}"


def _build_card_tags(case_type: str, language: str, metadata_source: str, legal_basis: list[str]) -> list[str]:
    tags: list[str] = []
    for value in [case_type, language, metadata_source]:
        normalized = value.strip()
        if normalized and normalized not in tags:
            tags.append(normalized)

    for basis in legal_basis[:2]:
        normalized_basis = basis.strip()
        if normalized_basis:
            tags.append(f"basis:{normalized_basis}")

    return tags


def build_case_card_ui_ready_output(
    query: str,
    top_k: int,
    model_metadata_path: Path,
    baseline_metadata_path: Path,
) -> CaseCardUIReadyOutput:
    pipeline = MetadataIntegratedResearchPipeline(
        model_metadata_path=model_metadata_path,
        baseline_metadata_path=baseline_metadata_path,
    )
    pipeline_result = pipeline.run(query=query, top_k=top_k)
    case_number_to_date = _build_case_number_to_date_map(query=query, top_k=top_k)

    cards: list[CaseCardUIReadyRecord] = []
    for source in pipeline_result.research_sources:
        decision_date = case_number_to_date.get(source.authoritative_case_number, "")
        card = CaseCardUIReadyRecord(
            authoritative_case_number=source.authoritative_case_number,
            authoritative_decision_date=decision_date,
            court=source.court,
            language=source.language,
            case_type=source.case_type,
            case_summary=source.case_summary,
            holding=source.holding,
            legal_basis=source.legal_basis,
            disputed_issues=source.disputed_issues,
            metadata_source=source.metadata_source,
            pdf_url=source.pdf_url,
            text_url_or_action=source.text_url_or_action,
            card_title=_build_card_title(
                case_number=source.authoritative_case_number,
                case_type=source.case_type,
                court=source.court,
            ),
            card_subtitle=_build_card_subtitle(
                language=source.language,
                decision_date=decision_date,
                metadata_source=source.metadata_source,
            ),
            card_tags=_build_card_tags(
                case_type=source.case_type,
                language=source.language,
                metadata_source=source.metadata_source,
                legal_basis=source.legal_basis,
            ),
        )
        cards.append(card)

    appears_successful = bool(cards) and all(
        bool(card.authoritative_case_number)
        and bool(card.court)
        and bool(card.language)
        and bool(card.case_type)
        and bool(card.pdf_url)
        and bool(card.text_url_or_action)
        and bool(card.card_title)
        and bool(card.card_subtitle)
        and card.metadata_source in {"model_generated", "deterministic_baseline"}
        for card in cards
    )

    return CaseCardUIReadyOutput(
        query_received=pipeline_result.query_received,
        retrieved_cases_count=pipeline_result.retrieved_cases_count,
        case_cards_built=len(cards),
        model_generated_metadata_used_count=pipeline_result.model_generated_metadata_used_count,
        deterministic_fallback_used_count=pipeline_result.deterministic_fallback_used_count,
        case_card_ui_ready_output_appears_successful=appears_successful,
        case_cards=cards,
    )


def write_report(output: CaseCardUIReadyOutput, output_path: Path) -> None:
    lines = [
        "Case Card UI-Ready Output Report - Day 51",
        f"query_received: {output.query_received}",
        f"retrieved_cases_count: {output.retrieved_cases_count}",
        f"case_cards_built: {output.case_cards_built}",
        f"model_generated_metadata_used_count: {output.model_generated_metadata_used_count}",
        f"deterministic_fallback_used_count: {output.deterministic_fallback_used_count}",
        (
            "case_card_ui_ready_output_appears_successful: "
            f"{output.case_card_ui_ready_output_appears_successful}"
        ),
        "",
        "case_cards:",
        json.dumps([asdict(item) for item in output.case_cards], ensure_ascii=False, indent=2),
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build UI-ready case-card output from metadata-integrated pipeline")
    parser.add_argument("--query", required=True, type=str, help="raw legal research query")
    parser.add_argument("--top_k", type=int, default=5, help="top-k retrieval results")
    parser.add_argument("--model-metadata", type=Path, default=DEFAULT_MODEL_METADATA_PATH)
    parser.add_argument("--baseline-metadata", type=Path, default=DEFAULT_BASELINE_METADATA_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--json", action="store_true", help="print full JSON output")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = build_case_card_ui_ready_output(
        query=args.query,
        top_k=max(args.top_k, 1),
        model_metadata_path=args.model_metadata,
        baseline_metadata_path=args.baseline_metadata,
    )
    write_report(output=output, output_path=args.output)

    print(f"query received: {output.query_received}")
    print(f"retrieved cases count: {output.retrieved_cases_count}")
    print(f"case cards built: {output.case_cards_built}")
    print(f"model-generated metadata used count: {output.model_generated_metadata_used_count}")
    print(f"deterministic fallback used count: {output.deterministic_fallback_used_count}")
    print(
        "whether case-card UI-ready output appears successful: "
        f"{output.case_card_ui_ready_output_appears_successful}"
    )

    if args.json:
        print(json.dumps(asdict(output), ensure_ascii=False, indent=2))

    return 0 if output.case_card_ui_ready_output_appears_successful else 1


if __name__ == "__main__":
    raise SystemExit(main())
