#!/usr/bin/env python3
"""Day 50: integrate generated case metadata into research pipeline output.

Pipeline shape:
query -> existing retrieval flow -> case-level metadata resolution -> enriched research output

Day 59 policy alignment:
- metadata attachment is treated as a post-merge stage over the authoritative merged corpus
- model-generated metadata remains preferred
- deterministic baseline remains fallback/benchmark/regression guard

Scope constraints:
- local-only
- no database integration
- no external API calls
- no cloud model calls
- no model-selection strategy changes
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from crawler.metadata.metadata_artifact_selection import resolve_model_metadata_path
from crawler.retrieval.hybrid_retrieval_with_decomposition import DecompositionAwareHybridRetriever

DEFAULT_MODEL_METADATA_PATH = Path("data/eval/model_generated_metadata_output.jsonl")
DEFAULT_BASELINE_METADATA_PATH = Path("data/eval/deterministic_metadata_extraction_baseline_output.jsonl")
DEFAULT_REPORT_PATH = Path("data/eval/integrated_metadata_research_pipeline_report.txt")

@dataclass(frozen=True)
class CaseMetadata:
    authoritative_case_number: str
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


@dataclass(frozen=True)
class IntegratedResearchPipelineResult:
    query_received: str
    retrieved_cases_count: int
    cases_enriched_with_metadata: int
    model_generated_metadata_used_count: int
    deterministic_fallback_used_count: int
    metadata_integrated_research_pipeline_appears_successful: bool
    selected_model_metadata_path: str
    selected_model_metadata_case_count: int
    research_sources: list[CaseMetadata]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file_obj:
        for line_no, line in enumerate(file_obj, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL row in {path} line {line_no}: {exc}") from exc
    return rows


def _normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _build_metadata_index(path: Path) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    if not path.exists():
        return index

    for payload in _load_jsonl(path):
        core = payload.get("core_case_metadata") or {}
        generated = payload.get("generated_digest_metadata") or {}
        case_number = str(
            core.get("authoritative_case_number")
            or payload.get("authoritative_case_number")
            or payload.get("case_number")
            or ""
        ).strip()
        if not case_number:
            continue

        index[case_number] = {
            "authoritative_case_number": case_number,
            "court": str(core.get("court") or payload.get("court") or "").strip(),
            "language": str(core.get("language") or payload.get("language") or "").strip(),
            "case_type": str(core.get("case_type") or payload.get("case_type") or "").strip(),
            "case_summary": str(generated.get("case_summary") or payload.get("case_summary") or "").strip(),
            "holding": str(generated.get("holding") or payload.get("holding") or "").strip(),
            "legal_basis": _normalize_string_list(generated.get("legal_basis") or payload.get("legal_basis")),
            "disputed_issues": _normalize_string_list(
                generated.get("disputed_issues") or payload.get("disputed_issues")
            ),
            "pdf_url": str(core.get("pdf_url") or payload.get("pdf_url") or "").strip(),
            "text_url_or_action": str(
                core.get("text_url_or_action") or payload.get("text_url_or_action") or ""
            ).strip(),
        }

    return index


def _is_metadata_complete(record: dict[str, Any]) -> bool:
    return all(
        bool(record.get(field))
        for field in [
            "authoritative_case_number",
            "court",
            "language",
            "case_type",
            "case_summary",
            "holding",
            "pdf_url",
            "text_url_or_action",
        ]
    ) and bool(record.get("legal_basis")) and bool(record.get("disputed_issues"))


def _fallback_from_hit(hit: object) -> dict[str, Any]:
    return {
        "authoritative_case_number": str(getattr(hit, "authoritative_case_number", "")).strip(),
        "court": str(getattr(hit, "court", "")).strip(),
        "language": str(getattr(hit, "language", "")).strip(),
        "case_type": str(getattr(hit, "case_type", "")).strip(),
        "case_summary": "",
        "holding": "",
        "legal_basis": [],
        "disputed_issues": [],
        "pdf_url": str(getattr(hit, "pdf_url", "")).strip(),
        "text_url_or_action": str(getattr(hit, "text_url_or_action", "")).strip(),
    }


class MetadataIntegratedResearchPipeline:
    def __init__(
        self,
        model_metadata_path: Path,
        baseline_metadata_path: Path,
        *,
        model_metadata_explicit_override: bool = False,
    ) -> None:
        self._retriever = DecompositionAwareHybridRetriever()
        selected = resolve_model_metadata_path(
            model_metadata_path,
            default_path=DEFAULT_MODEL_METADATA_PATH,
            explicit_override=model_metadata_explicit_override,
        )
        self.selected_model_metadata_path = selected.path
        self.selected_model_metadata_case_count = selected.case_count
        self.selected_model_metadata_source = selected.source

        self._model_index = _build_metadata_index(self.selected_model_metadata_path)
        self._baseline_index = _build_metadata_index(baseline_metadata_path)

    def run(self, query: str, top_k: int) -> IntegratedResearchPipelineResult:
        retrieval_result = self._retriever.retrieve(query=query, top_k=top_k, decompose=True)

        case_hits: dict[str, object] = {}
        for hit in retrieval_result.hits:
            case_number = str(getattr(hit, "authoritative_case_number", "")).strip()
            if case_number and case_number not in case_hits:
                case_hits[case_number] = hit

        enriched: list[CaseMetadata] = []
        model_count = 0
        baseline_count = 0

        for case_number, hit in case_hits.items():
            model_record = self._model_index.get(case_number)
            baseline_record = self._baseline_index.get(case_number)

            if model_record and _is_metadata_complete(model_record):
                chosen = model_record
                source = "model_generated"
                model_count += 1
            elif baseline_record and _is_metadata_complete(baseline_record):
                chosen = baseline_record
                source = "deterministic_baseline"
                baseline_count += 1
            elif model_record:
                chosen = model_record
                source = "model_generated"
                model_count += 1
            elif baseline_record:
                chosen = baseline_record
                source = "deterministic_baseline"
                baseline_count += 1
            else:
                chosen = _fallback_from_hit(hit)
                source = "deterministic_baseline"
                baseline_count += 1

            enriched.append(
                CaseMetadata(
                    authoritative_case_number=chosen["authoritative_case_number"] or case_number,
                    court=chosen["court"] or str(getattr(hit, "court", "")).strip(),
                    language=chosen["language"] or str(getattr(hit, "language", "")).strip(),
                    case_type=chosen["case_type"] or str(getattr(hit, "case_type", "")).strip(),
                    case_summary=chosen.get("case_summary", ""),
                    holding=chosen.get("holding", ""),
                    legal_basis=chosen.get("legal_basis", []),
                    disputed_issues=chosen.get("disputed_issues", []),
                    metadata_source=source,
                    pdf_url=chosen["pdf_url"] or str(getattr(hit, "pdf_url", "")).strip(),
                    text_url_or_action=chosen["text_url_or_action"]
                    or str(getattr(hit, "text_url_or_action", "")).strip(),
                )
            )

        appears_successful = bool(enriched) and all(
            all(getattr(item, field) for field in ["authoritative_case_number", "court", "language", "case_type"])
            and isinstance(item.legal_basis, list)
            and isinstance(item.disputed_issues, list)
            and item.metadata_source in {"model_generated", "deterministic_baseline"}
            and bool(item.pdf_url)
            and bool(item.text_url_or_action)
            for item in enriched
        )

        return IntegratedResearchPipelineResult(
            query_received=query,
            retrieved_cases_count=len(case_hits),
            cases_enriched_with_metadata=len(enriched),
            model_generated_metadata_used_count=model_count,
            deterministic_fallback_used_count=baseline_count,
            metadata_integrated_research_pipeline_appears_successful=appears_successful,
            selected_model_metadata_path=str(self.selected_model_metadata_path),
            selected_model_metadata_case_count=self.selected_model_metadata_case_count,
            research_sources=enriched,
        )


def write_report(result: IntegratedResearchPipelineResult, output_path: Path) -> None:
    lines = [
        "Integrated Metadata Research Pipeline Report - Day 50",
        f"query_received: {result.query_received}",
        f"retrieved_cases_count: {result.retrieved_cases_count}",
        f"cases_enriched_with_metadata: {result.cases_enriched_with_metadata}",
        f"model_generated_metadata_used_count: {result.model_generated_metadata_used_count}",
        f"deterministic_fallback_used_count: {result.deterministic_fallback_used_count}",
        (
            "metadata_integrated_research_pipeline_appears_successful: "
            f"{result.metadata_integrated_research_pipeline_appears_successful}"
        ),
        f"selected_model_metadata_path: {result.selected_model_metadata_path}",
        f"selected_model_metadata_case_count: {result.selected_model_metadata_case_count}",
        "",
        "research_sources:",
        json.dumps([asdict(item) for item in result.research_sources], ensure_ascii=False, indent=2),
    ]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Integrate case-level metadata into research pipeline output")
    parser.add_argument("--query", required=True, type=str, help="raw legal research query")
    parser.add_argument("--top_k", type=int, default=5, help="top-k merged retrieval hits")
    parser.add_argument("--model-metadata", type=Path, default=DEFAULT_MODEL_METADATA_PATH)
    parser.add_argument("--baseline-metadata", type=Path, default=DEFAULT_BASELINE_METADATA_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--json", action="store_true", help="print full JSON result")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    pipeline = MetadataIntegratedResearchPipeline(
        model_metadata_path=args.model_metadata,
        baseline_metadata_path=args.baseline_metadata,
        model_metadata_explicit_override="--model-metadata" in sys.argv,
    )
    result = pipeline.run(query=args.query, top_k=max(args.top_k, 1))
    write_report(result=result, output_path=args.output)

    print(f"query received: {result.query_received}")
    print(f"retrieved cases count: {result.retrieved_cases_count}")
    print(f"cases enriched with metadata: {result.cases_enriched_with_metadata}")
    print(f"model-generated metadata used count: {result.model_generated_metadata_used_count}")
    print(f"deterministic fallback used count: {result.deterministic_fallback_used_count}")
    print(
        "whether metadata-integrated research pipeline appears successful: "
        f"{result.metadata_integrated_research_pipeline_appears_successful}"
    )
    print(f"selected model metadata output path: {result.selected_model_metadata_path}")
    print(f"selected model metadata case count: {result.selected_model_metadata_case_count}")

    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))

    return 0 if result.metadata_integrated_research_pipeline_appears_successful else 1


if __name__ == "__main__":
    raise SystemExit(main())
