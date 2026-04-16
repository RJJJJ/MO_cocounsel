#!/usr/bin/env python3
"""Day 44: local metadata model prompt/eval loop runner.

Builds a repeatable local-only loop for comparing prompt versions on sample cases.

Scope constraints:
- local-only
- no database
- no external/cloud API
- no vector retrieval
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_INPUT_PATH = Path("data/corpus/prepared/macau_court_cases/bm25_chunks.jsonl")
DEFAULT_BASELINE_PATH = Path("data/eval/deterministic_metadata_extraction_baseline_output.jsonl")
DEFAULT_EVAL_SET_PATH = Path("data/eval/metadata_field_evaluation_set.jsonl")
DEFAULT_OUTPUT_DIR = Path("data/eval/metadata_prompt_eval_loop")
DEFAULT_REPORT_PATH = Path("data/eval/metadata_model_prompt_eval_loop_report.txt")
DEFAULT_PROMPT_VERSIONS = "day44_prompt_a,day44_prompt_b"
DEFAULT_MODEL_NAMES = "qwen2.5:7b-instruct"

GENERATION_FIELDS = ["case_summary", "holding", "legal_basis", "disputed_issues"]


@dataclass(frozen=True)
class LoopRunSummary:
    model_name: str
    prompt_version: str
    sample_cases_used: list[str]
    generation_success_count: int
    generation_total_count: int
    fields_generated: dict[str, int]
    evaluation_ready: bool
    comparison_ready: bool
    eval_run_completed: bool
    comparison_run_completed: bool
    output_jsonl_path: Path


def _run_python_command(command: list[str]) -> subprocess.CompletedProcess[str]:
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


def _extract_sample_cases(records: list[dict[str, Any]]) -> list[str]:
    case_numbers: list[str] = []
    for row in records:
        case_number = str(row.get("core_case_metadata", {}).get("authoritative_case_number", "")).strip()
        if case_number:
            case_numbers.append(case_number)
    return case_numbers


def _count_fields_generated(records: list[dict[str, Any]]) -> dict[str, int]:
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


def _parse_comparison_ready(report_path: Path) -> bool:
    if not report_path.exists():
        return False
    text = report_path.read_text(encoding="utf-8")
    return "comparison-ready: yes" in text


def run_single_prompt_eval(
    *,
    input_path: Path,
    baseline_path: Path,
    eval_set_path: Path,
    output_dir: Path,
    model_name: str,
    prompt_version: str,
    backend: str,
    command_template: str,
    timeout_seconds: int,
    sample_case_limit: int,
    language: str,
    case_numbers: str,
    max_input_chars: int,
) -> LoopRunSummary:
    safe_model = model_name.replace(":", "_").replace("/", "_")
    safe_prompt = prompt_version.replace(":", "_").replace("/", "_")

    model_output = output_dir / f"model_output__{safe_model}__{safe_prompt}.jsonl"
    generation_report = output_dir / f"generation_report__{safe_model}__{safe_prompt}.txt"
    eval_report = output_dir / f"field_eval_report__{safe_model}__{safe_prompt}.txt"
    comparison_report = output_dir / f"comparison_report__{safe_model}__{safe_prompt}.txt"

    generation_cmd = [
        sys.executable,
        "crawler/metadata/connect_local_chinese_model_metadata_generation.py",
        "--input",
        str(input_path),
        "--output",
        str(model_output),
        "--report",
        str(generation_report),
        "--sample-case-limit",
        str(sample_case_limit),
        "--language",
        language,
        "--case-numbers",
        case_numbers,
        "--model-name",
        model_name,
        "--prompt-version",
        prompt_version,
        "--backend",
        backend,
        "--timeout-seconds",
        str(timeout_seconds),
        "--max-input-chars",
        str(max_input_chars),
    ]
    if backend == "command" and command_template.strip():
        generation_cmd.extend(["--command-template", command_template.strip()])

    generation_result = _run_python_command(generation_cmd)

    records = _load_jsonl(model_output)
    success_count = sum(1 for row in records if row.get("generation_status") == "local_model_generated")
    sample_cases_used = _extract_sample_cases(records)
    fields_generated = _count_fields_generated(records)

    eval_run_completed = False
    if eval_set_path.exists() and model_output.exists():
        eval_cmd = [
            sys.executable,
            "crawler/metadata/run_metadata_field_evaluation.py",
            "--eval-set",
            str(eval_set_path),
            "--predictions",
            str(model_output),
            "--report",
            str(eval_report),
        ]
        eval_result = _run_python_command(eval_cmd)
        eval_run_completed = eval_result.returncode == 0 and eval_report.exists()

    comparison_run_completed = False
    comparison_ready = False
    if baseline_path.exists() and model_output.exists():
        compare_cmd = [
            sys.executable,
            "crawler/metadata/build_metadata_generation_comparison_harness.py",
            "--baseline-input",
            str(baseline_path),
            "--model-input",
            str(model_output),
            "--report-output",
            str(comparison_report),
        ]
        compare_result = _run_python_command(compare_cmd)
        comparison_run_completed = compare_result.returncode == 0 and comparison_report.exists()
        comparison_ready = _parse_comparison_ready(comparison_report)

    required_fields_present = all(field in fields_generated for field in GENERATION_FIELDS)
    has_any_field_content = any(count > 0 for count in fields_generated.values())
    evaluation_ready = generation_result.returncode == 0 and success_count > 0 and required_fields_present and has_any_field_content

    return LoopRunSummary(
        model_name=model_name,
        prompt_version=prompt_version,
        sample_cases_used=sample_cases_used,
        generation_success_count=success_count,
        generation_total_count=len(records),
        fields_generated=fields_generated,
        evaluation_ready=evaluation_ready,
        comparison_ready=comparison_ready,
        eval_run_completed=eval_run_completed,
        comparison_run_completed=comparison_run_completed,
        output_jsonl_path=model_output,
    )


def build_loop_report(summaries: list[LoopRunSummary], report_path: Path) -> str:
    lines: list[str] = [
        "Metadata Model Prompt/Eval Loop Report - Day 44",
        f"report_path: {report_path}",
        "",
    ]

    for idx, summary in enumerate(summaries, start=1):
        lines.extend(
            [
                f"=== run_{idx} ===",
                f"model_name: {summary.model_name}",
                f"prompt_version: {summary.prompt_version}",
                f"sample cases used: {summary.sample_cases_used}",
                f"generation success count: {summary.generation_success_count}",
                f"generation total count: {summary.generation_total_count}",
                f"fields generated: {summary.fields_generated}",
                f"evaluation-ready: {'yes' if summary.evaluation_ready else 'no'}",
                f"comparison-ready: {'yes' if summary.comparison_ready else 'no'}",
                f"eval run completed: {'yes' if summary.eval_run_completed else 'no'}",
                f"comparison run completed: {'yes' if summary.comparison_run_completed else 'no'}",
                f"model_output_path: {summary.output_jsonl_path}",
                "",
            ]
        )

    prompts = sorted({item.prompt_version for item in summaries})
    total_sample_cases = sum(len(item.sample_cases_used) for item in summaries)
    total_success = sum(item.generation_success_count for item in summaries)
    total_comparison_runs = sum(1 for item in summaries if item.comparison_run_completed)
    loop_success = bool(summaries) and total_success > 0 and total_comparison_runs > 0

    lines.extend(
        [
            "=== Aggregated Summary ===",
            f"prompt versions evaluated: {prompts}",
            f"sample cases processed: {total_sample_cases}",
            f"successful generations: {total_success}",
            f"comparison runs completed: {total_comparison_runs}",
            f"whether metadata model prompt/eval loop appears successful: {loop_success}",
        ]
    )

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build local metadata model prompt/eval loop (Day 44).")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--baseline-input", type=Path, default=DEFAULT_BASELINE_PATH)
    parser.add_argument("--eval-set", type=Path, default=DEFAULT_EVAL_SET_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--prompt-versions", default=DEFAULT_PROMPT_VERSIONS, help="Comma-separated prompt versions.")
    parser.add_argument("--model-names", default=DEFAULT_MODEL_NAMES, help="Comma-separated model names.")
    parser.add_argument("--backend", choices=["ollama_cli", "command"], default="ollama_cli")
    parser.add_argument("--command-template", default="", help="Used when --backend command.")
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--sample-case-limit", type=int, default=5)
    parser.add_argument("--language", default="zh")
    parser.add_argument("--case-numbers", default="", help="Comma-separated authoritative case numbers.")
    parser.add_argument("--max-input-chars", type=int, default=8000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Input chunks file not found: {args.input}")

    prompt_versions = [item.strip() for item in args.prompt_versions.split(",") if item.strip()]
    model_names = [item.strip() for item in args.model_names.split(",") if item.strip()]
    if not prompt_versions:
        raise ValueError("At least one prompt version is required")
    if not model_names:
        raise ValueError("At least one model name is required")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    summaries: list[LoopRunSummary] = []
    for model_name in model_names:
        for prompt_version in prompt_versions:
            summary = run_single_prompt_eval(
                input_path=args.input,
                baseline_path=args.baseline_input,
                eval_set_path=args.eval_set,
                output_dir=args.output_dir,
                model_name=model_name,
                prompt_version=prompt_version,
                backend=args.backend,
                command_template=args.command_template,
                timeout_seconds=max(1, args.timeout_seconds),
                sample_case_limit=max(1, args.sample_case_limit),
                language=args.language.strip().lower(),
                case_numbers=args.case_numbers,
                max_input_chars=max(1000, args.max_input_chars),
            )
            summaries.append(summary)

    report_text = build_loop_report(summaries=summaries, report_path=args.report)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report_text, encoding="utf-8")

    prompts = sorted({item.prompt_version for item in summaries})
    total_cases = sum(len(item.sample_cases_used) for item in summaries)
    total_success = sum(item.generation_success_count for item in summaries)
    comparison_runs = sum(1 for item in summaries if item.comparison_run_completed)
    loop_success = bool(summaries) and total_success > 0 and comparison_runs > 0

    print(f"prompt versions evaluated: {prompts}")
    print(f"sample cases processed: {total_cases}")
    print(f"successful generations: {total_success}")
    print(f"comparison runs completed: {comparison_runs}")
    print(f"whether metadata model prompt/eval loop appears successful: {loop_success}")
    print(f"report written: {args.report}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
