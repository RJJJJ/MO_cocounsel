#!/usr/bin/env python3
"""Day 53: fix and verify latest-output selection for model-generated metadata artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from crawler.metadata.build_metadata_generation_comparison_harness import (
    DEFAULT_BASELINE_PATH,
    DEFAULT_REPORT_PATH as DEFAULT_COMPARISON_REPORT_PATH,
    build_report_lines,
    load_case_metadata,
)
from crawler.metadata.metadata_artifact_selection import (
    inspect_metadata_artifact,
    resolve_model_metadata_path,
)
from crawler.pipeline.build_api_ready_response_envelope import build_api_ready_response_envelope
from crawler.pipeline.build_case_card_ui_ready_output import build_case_card_ui_ready_output
from crawler.pipeline.integrate_metadata_into_research_pipeline import (
    DEFAULT_BASELINE_METADATA_PATH,
    DEFAULT_MODEL_METADATA_PATH,
    MetadataIntegratedResearchPipeline,
)

DEFAULT_REPORT_PATH = Path("data/eval/fixed_metadata_latest_output_selection_report.txt")
DEFAULT_QUERY = "澳門 勞動 合同 終止"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fix metadata latest-output selection and verify downstream usage")
    parser.add_argument("--model-metadata", type=Path, default=DEFAULT_MODEL_METADATA_PATH)
    parser.add_argument("--baseline-metadata", type=Path, default=DEFAULT_BASELINE_METADATA_PATH)
    parser.add_argument("--comparison-report", type=Path, default=DEFAULT_COMPARISON_REPORT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--query", type=str, default=DEFAULT_QUERY)
    parser.add_argument("--top-k", type=int, default=5)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.baseline_metadata.exists():
        raise FileNotFoundError(f"Baseline metadata not found: {args.baseline_metadata}")

    selected = resolve_model_metadata_path(
        args.model_metadata,
        default_path=DEFAULT_MODEL_METADATA_PATH,
        explicit_override="--model-metadata" in sys.argv,
    )
    default_candidate = inspect_metadata_artifact(DEFAULT_MODEL_METADATA_PATH)
    selected_candidate = inspect_metadata_artifact(selected.path)

    stale_path_detected = (
        DEFAULT_MODEL_METADATA_PATH.exists()
        and selected.path != DEFAULT_MODEL_METADATA_PATH
        and default_candidate.case_count > 0
    )

    baseline_records = load_case_metadata(DEFAULT_BASELINE_PATH)
    model_records = load_case_metadata(selected.path)
    comparison_lines, comparison_summary = build_report_lines(
        baseline_records=baseline_records,
        model_records=model_records,
    )

    args.comparison_report.parent.mkdir(parents=True, exist_ok=True)
    args.comparison_report.write_text("\n".join(comparison_lines) + "\n", encoding="utf-8")

    pipeline = MetadataIntegratedResearchPipeline(
        model_metadata_path=args.model_metadata,
        baseline_metadata_path=args.baseline_metadata,
        model_metadata_explicit_override="--model-metadata" in sys.argv,
    )
    pipeline_result = pipeline.run(query=args.query, top_k=max(args.top_k, 1))

    case_card = build_case_card_ui_ready_output(
        query=args.query,
        top_k=max(args.top_k, 1),
        model_metadata_path=args.model_metadata,
        baseline_metadata_path=args.baseline_metadata,
        model_metadata_explicit_override="--model-metadata" in sys.argv,
    )
    envelope = build_api_ready_response_envelope(
        query=args.query,
        top_k=max(args.top_k, 1),
        model_metadata_path=args.model_metadata,
        baseline_metadata_path=args.baseline_metadata,
        model_metadata_explicit_override="--model-metadata" in sys.argv,
    )

    downstream_consistent = (
        pipeline_result.selected_model_metadata_path
        == case_card.selected_model_metadata_path
        == envelope.diagnostics.selected_model_metadata_path
        == str(selected.path)
    )
    appears_successful = selected_candidate.case_count > default_candidate.case_count and downstream_consistent

    lines = [
        "Fixed Metadata Latest Output Selection Report - Day 53",
        f"selected model metadata output path: {selected.path}",
        f"selected model metadata case count: {selected.case_count}",
        f"selected source: {selected.source}",
        f"previous stale path detected: {'yes' if stale_path_detected else 'no'}",
        f"default path case count: {default_candidate.case_count}",
        f"comparison harness cases loaded: {comparison_summary['model_generated_cases_loaded']}",
        f"comparison harness report path: {args.comparison_report}",
        f"pipeline selected path: {pipeline_result.selected_model_metadata_path}",
        f"case-card selected path: {case_card.selected_model_metadata_path}",
        f"api-envelope selected path: {envelope.diagnostics.selected_model_metadata_path}",
        f"downstream selection consistent: {'yes' if downstream_consistent else 'no'}",
        (
            "whether latest-output selection fix appears successful: "
            f"{'yes' if appears_successful else 'no'}"
        ),
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")

    for line in lines[1:]:
        print(line)

    return 0 if appears_successful else 1


if __name__ == "__main__":
    raise SystemExit(main())
