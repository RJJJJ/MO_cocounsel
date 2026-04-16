#!/usr/bin/env python3
"""Day 52: build API-ready response envelope over case-card / UI-ready output layer.

Flow:
query -> existing case-card / UI-ready output layer -> API-ready response envelope

Scope constraints:
- local-only
- no database integration
- no external API calls
- no cloud model calls
- response shaping only (no retrieval / metadata logic changes)
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

from crawler.pipeline.build_case_card_ui_ready_output import (
    DEFAULT_REPORT_PATH as DEFAULT_CASE_CARD_REPORT_PATH,
    CaseCardUIReadyRecord,
    build_case_card_ui_ready_output,
)
from crawler.pipeline.integrate_metadata_into_research_pipeline import (
    DEFAULT_BASELINE_METADATA_PATH,
    DEFAULT_MODEL_METADATA_PATH,
)

DEFAULT_REPORT_PATH = Path("data/eval/api_ready_response_envelope_report.txt")
DEFAULT_SCHEMA_VERSION = "v1"


@dataclass(frozen=True)
class ResponseDiagnostics:
    retrieved_cases_count: int
    case_cards_built: int
    model_generated_metadata_used_count: int
    deterministic_fallback_used_count: int
    success_flag: bool


@dataclass(frozen=True)
class APIReadyResponseEnvelope:
    schema_version: str
    query: str
    top_k: int
    result_count: int
    diagnostics: ResponseDiagnostics
    results: list[CaseCardUIReadyRecord]


def build_api_ready_response_envelope(
    query: str,
    top_k: int,
    model_metadata_path: Path,
    baseline_metadata_path: Path,
) -> APIReadyResponseEnvelope:
    case_card_output = build_case_card_ui_ready_output(
        query=query,
        top_k=top_k,
        model_metadata_path=model_metadata_path,
        baseline_metadata_path=baseline_metadata_path,
    )

    diagnostics = ResponseDiagnostics(
        retrieved_cases_count=case_card_output.retrieved_cases_count,
        case_cards_built=case_card_output.case_cards_built,
        model_generated_metadata_used_count=case_card_output.model_generated_metadata_used_count,
        deterministic_fallback_used_count=case_card_output.deterministic_fallback_used_count,
        success_flag=case_card_output.case_card_ui_ready_output_appears_successful,
    )

    return APIReadyResponseEnvelope(
        schema_version=DEFAULT_SCHEMA_VERSION,
        query=case_card_output.query_received,
        top_k=max(top_k, 1),
        result_count=len(case_card_output.case_cards),
        diagnostics=diagnostics,
        results=case_card_output.case_cards,
    )


def write_report(envelope: APIReadyResponseEnvelope, output_path: Path) -> None:
    lines = [
        "API-Ready Response Envelope Report - Day 52",
        f"schema_version: {envelope.schema_version}",
        f"query: {envelope.query}",
        f"top_k: {envelope.top_k}",
        f"result_count: {envelope.result_count}",
        "diagnostics:",
        f"  retrieved_cases_count: {envelope.diagnostics.retrieved_cases_count}",
        f"  case_cards_built: {envelope.diagnostics.case_cards_built}",
        (
            "  model_generated_metadata_used_count: "
            f"{envelope.diagnostics.model_generated_metadata_used_count}"
        ),
        (
            "  deterministic_fallback_used_count: "
            f"{envelope.diagnostics.deterministic_fallback_used_count}"
        ),
        f"  success_flag: {envelope.diagnostics.success_flag}",
        "",
        "results:",
        json.dumps([asdict(item) for item in envelope.results], ensure_ascii=False, indent=2),
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build API-ready response envelope over UI-ready case cards")
    parser.add_argument("--query", required=True, type=str, help="raw legal research query")
    parser.add_argument("--top_k", type=int, default=5, help="top-k retrieval results")
    parser.add_argument("--model-metadata", type=Path, default=DEFAULT_MODEL_METADATA_PATH)
    parser.add_argument("--baseline-metadata", type=Path, default=DEFAULT_BASELINE_METADATA_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--json", action="store_true", help="print full JSON envelope")
    parser.add_argument(
        "--also-write-case-card-report",
        action="store_true",
        help="also emit Day 51 case-card report for debugging",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    normalized_top_k = max(args.top_k, 1)

    envelope = build_api_ready_response_envelope(
        query=args.query,
        top_k=normalized_top_k,
        model_metadata_path=args.model_metadata,
        baseline_metadata_path=args.baseline_metadata,
    )
    write_report(envelope=envelope, output_path=args.output)

    if args.also_write_case_card_report:
        case_card_output = build_case_card_ui_ready_output(
            query=args.query,
            top_k=normalized_top_k,
            model_metadata_path=args.model_metadata,
            baseline_metadata_path=args.baseline_metadata,
        )
        from crawler.pipeline.build_case_card_ui_ready_output import write_report as write_case_card_report

        write_case_card_report(case_card_output, DEFAULT_CASE_CARD_REPORT_PATH)

    print(f"query received: {envelope.query}")
    print(f"result_count: {envelope.result_count}")
    print("envelope built: yes")
    print(
        "whether API-ready response envelope appears successful: "
        f"{envelope.diagnostics.success_flag}"
    )

    if args.json:
        print(json.dumps(asdict(envelope), ensure_ascii=False, indent=2))

    return 0 if envelope.diagnostics.success_flag else 1


if __name__ == "__main__":
    raise SystemExit(main())
