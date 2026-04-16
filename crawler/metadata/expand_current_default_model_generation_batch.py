#!/usr/bin/env python3
"""Day 49: keep current default model and expand metadata generation batch.

This script intentionally keeps the current default local model unchanged:
- model_name = qwen2.5:3b-instruct
- prompt_version = day45_prompt_b_tch_norm
- Traditional Chinese normalization enabled via generation path

Scope constraints:
- local-only model backend
- no database
- no external/cloud API
- no vector retrieval
- comparison-harness compatible output schema
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

GENERATION_FIELDS = ["case_summary", "holding", "legal_basis", "disputed_issues"]

DEFAULT_INPUT_PATH = Path("data/corpus/prepared/macau_court_cases/bm25_chunks.jsonl")
DEFAULT_OUTPUT_JSONL = Path("data/eval/expanded_current_default_model_generation_batch_output.jsonl")
DEFAULT_INTERNAL_GENERATION_REPORT = Path("data/eval/expanded_current_default_model_generation_inner_report.txt")
DEFAULT_FINAL_REPORT = Path("data/eval/expanded_current_default_model_generation_batch_report.txt")
DEFAULT_BASELINE_PATH = Path("data/eval/deterministic_metadata_extraction_baseline_output.jsonl")

FIXED_MODEL_NAME = "qwen2.5:3b-instruct"
FIXED_PROMPT_VERSION = "day45_prompt_b_tch_norm"


@dataclass(frozen=True)
class ExpandedBatchSummary:
    selected_case_numbers: list[str]
    generation_success_count: int
    generation_total_count: int
    field_completeness: dict[str, int]
    script_normalization_applied_count: int
    runtime_seconds: float
    comparison_harness_compatible: bool


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows

    with path.open("r", encoding="utf-8") as file_obj:
        for line in file_obj:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _extract_case_numbers(records: list[dict[str, Any]]) -> list[str]:
    case_numbers: list[str] = []
    for row in records:
        case_number = str(row.get("core_case_metadata", {}).get("authoritative_case_number", "")).strip()
        if case_number:
            case_numbers.append(case_number)
    return case_numbers


def _calc_field_completeness(records: list[dict[str, Any]]) -> dict[str, int]:
    counts = {field: 0 for field in GENERATION_FIELDS}
    for row in records:
        generated = row.get("generated_digest_metadata", {})
        for field in GENERATION_FIELDS:
            value = generated.get(field)
            if isinstance(value, list):
                if any(str(item).strip() for item in value):
                    counts[field] += 1
            elif str(value or "").strip():
                counts[field] += 1
    return counts


def _calc_normalization_applied(records: list[dict[str, Any]]) -> int:
    return sum(1 for row in records if bool(row.get("script_normalization_applied")))


def _is_comparison_harness_compatible(records: list[dict[str, Any]]) -> bool:
    required_core = {"authoritative_case_number", "language"}
    for row in records:
        core = row.get("core_case_metadata")
        generated = row.get("generated_digest_metadata")
        if not isinstance(core, dict) or not isinstance(generated, dict):
            return False
        if not required_core.issubset(set(core.keys())):
            return False
        if not all(field in generated for field in GENERATION_FIELDS):
            return False
    return True


def _run_expanded_generation(
    *,
    input_path: Path,
    output_jsonl: Path,
    generation_report_path: Path,
    backend: str,
    command_template: str,
    timeout_seconds: int,
    sample_case_limit: int,
    language: str,
    case_numbers: str,
    max_input_chars: int,
) -> ExpandedBatchSummary:
    command = [
        sys.executable,
        "crawler/metadata/connect_local_chinese_model_metadata_generation.py",
        "--input",
        str(input_path),
        "--output",
        str(output_jsonl),
        "--report",
        str(generation_report_path),
        "--sample-case-limit",
        str(sample_case_limit),
        "--language",
        language,
        "--case-numbers",
        case_numbers,
        "--model-name",
        FIXED_MODEL_NAME,
        "--prompt-version",
        FIXED_PROMPT_VERSION,
        "--backend",
        backend,
        "--timeout-seconds",
        str(timeout_seconds),
        "--max-input-chars",
        str(max_input_chars),
    ]
    if backend == "command" and command_template.strip():
        command.extend(["--command-template", command_template.strip()])

    start = time.perf_counter()
    result = _run_command(command)
    runtime_seconds = time.perf_counter() - start

    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"expanded generation failed: {message}")

    records = _load_jsonl(output_jsonl)
    success_count = sum(1 for row in records if row.get("generation_status") == "local_model_generated")

    return ExpandedBatchSummary(
        selected_case_numbers=_extract_case_numbers(records),
        generation_success_count=success_count,
        generation_total_count=len(records),
        field_completeness=_calc_field_completeness(records),
        script_normalization_applied_count=_calc_normalization_applied(records),
        runtime_seconds=runtime_seconds,
        comparison_harness_compatible=_is_comparison_harness_compatible(records),
    )


def _build_report(
    *,
    report_path: Path,
    output_jsonl: Path,
    generation_report_path: Path,
    baseline_path: Path,
    summary: ExpandedBatchSummary,
) -> str:
    overall_success = (
        summary.generation_total_count > 0
        and summary.generation_success_count > 0
        and summary.comparison_harness_compatible
    )

    lines = [
        "Expanded Current Default Model Generation Batch Report - Day 49",
        f"report_path: {report_path}",
        "",
        "=== Fixed Conditions ===",
        f"current default model used: {FIXED_MODEL_NAME}",
        f"prompt version fixed: {FIXED_PROMPT_VERSION}",
        "Traditional Chinese normalization enabled: yes",
        "deterministic baseline remains benchmark/fallback: yes",
        "",
        "=== Local Paths ===",
        f"input_chunks_path: {DEFAULT_INPUT_PATH}",
        f"output_jsonl_path: {output_jsonl}",
        f"inner_generation_report_path: {generation_report_path}",
        f"deterministic_baseline_path: {baseline_path}",
        "",
        "=== Expanded Batch Summary ===",
        f"sample cases selected: {summary.selected_case_numbers}",
        f"sample_case_count: {len(summary.selected_case_numbers)}",
        f"generation success count: {summary.generation_success_count}",
        f"generation total count: {summary.generation_total_count}",
        f"field completeness: {summary.field_completeness}",
        "script normalization applied yes/no: "
        f"{summary.script_normalization_applied_count > 0}",
        f"script normalization applied count: {summary.script_normalization_applied_count}",
        f"comparison harness compatible yes/no: {summary.comparison_harness_compatible}",
        f"runtime seconds: {summary.runtime_seconds:.2f}",
        "whether expanded current-default batch appears successful: "
        f"{overall_success}",
    ]
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Expand current-default local metadata generation batch (Day 49)."
    )
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_JSONL)
    parser.add_argument("--generation-report", type=Path, default=DEFAULT_INTERNAL_GENERATION_REPORT)
    parser.add_argument("--report", type=Path, default=DEFAULT_FINAL_REPORT)
    parser.add_argument("--baseline-input", type=Path, default=DEFAULT_BASELINE_PATH)
    parser.add_argument("--sample-case-limit", type=int, default=24)
    parser.add_argument("--language", default="zh")
    parser.add_argument("--case-numbers", default="")
    parser.add_argument("--backend", choices=["ollama_cli", "command"], default="ollama_cli")
    parser.add_argument("--command-template", default="")
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--max-input-chars", type=int, default=8000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Input chunks file not found: {args.input}")

    summary = _run_expanded_generation(
        input_path=args.input,
        output_jsonl=args.output,
        generation_report_path=args.generation_report,
        backend=args.backend,
        command_template=args.command_template,
        timeout_seconds=max(args.timeout_seconds, 1),
        sample_case_limit=max(args.sample_case_limit, 1),
        language=args.language.strip().lower(),
        case_numbers=args.case_numbers,
        max_input_chars=max(args.max_input_chars, 1),
    )

    report_text = _build_report(
        report_path=args.report,
        output_jsonl=args.output,
        generation_report_path=args.generation_report,
        baseline_path=args.baseline_input,
        summary=summary,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report_text, encoding="utf-8")

    overall_success = (
        summary.generation_total_count > 0
        and summary.generation_success_count > 0
        and summary.comparison_harness_compatible
    )

    print(f"current default model used: {FIXED_MODEL_NAME}")
    print(f"prompt version fixed: {FIXED_PROMPT_VERSION}")
    print(f"sample cases selected: {summary.selected_case_numbers}")
    print(f"generation success count: {summary.generation_success_count}")
    print(f"generation total count: {summary.generation_total_count}")
    print(f"field completeness: {summary.field_completeness}")
    print(f"script normalization applied yes/no: {summary.script_normalization_applied_count > 0}")
    print(f"whether expanded current-default batch appears successful: {overall_success}")
    print(f"output written: {args.output}")
    print(f"report written: {args.report}")

    return 0 if overall_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
