#!/usr/bin/env python3
"""Day 48: re-benchmark upgraded local model candidate under fixed best prompt.

Runs a controlled re-benchmark between:
- current default local model: qwen2.5:3b-instruct
- upgraded local model candidate: configurable

Scope constraints:
- local-only model backend
- no database
- no external/cloud API
- no vector retrieval
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
DEFAULT_OUTPUT_DIR = Path("data/eval/upgraded_local_model_candidate_benchmark")
DEFAULT_REPORT_PATH = Path("data/eval/rebenchmark_upgraded_local_model_candidate_report.txt")
DEFAULT_PROMPT_VERSION = "day45_prompt_b_tch_norm"
DEFAULT_CURRENT_MODEL = "qwen2.5:3b-instruct"
DEFAULT_CANDIDATE_MODEL = "qwen3:4b-instruct"


@dataclass(frozen=True)
class ModelRunSummary:
    model_name: str
    prompt_version: str
    output_jsonl_path: Path
    generation_report_path: Path
    sample_cases_used: list[str]
    generation_success_count: int
    generation_total_count: int
    field_completeness: dict[str, int]
    script_normalization_applied_count: int
    runtime_seconds: float


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


def _extract_sample_cases(records: list[dict[str, Any]]) -> list[str]:
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


def _run_generation_once(
    *,
    input_path: Path,
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
    label: str,
) -> ModelRunSummary:
    safe_model = model_name.replace(":", "_").replace("/", "_")
    safe_prompt = prompt_version.replace(":", "_").replace("/", "_")

    output_jsonl = output_dir / f"{label}__{safe_model}__{safe_prompt}.jsonl"
    generation_report = output_dir / f"{label}__{safe_model}__{safe_prompt}_generation_report.txt"

    command = [
        sys.executable,
        "crawler/metadata/connect_local_chinese_model_metadata_generation.py",
        "--input",
        str(input_path),
        "--output",
        str(output_jsonl),
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
        command.extend(["--command-template", command_template.strip()])

    start = time.perf_counter()
    result = _run_command(command)
    runtime_seconds = time.perf_counter() - start

    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip()
        raise RuntimeError(f"generation run failed for model {model_name}: {message}")

    records = _load_jsonl(output_jsonl)
    success_count = sum(1 for row in records if row.get("generation_status") == "local_model_generated")

    return ModelRunSummary(
        model_name=model_name,
        prompt_version=prompt_version,
        output_jsonl_path=output_jsonl,
        generation_report_path=generation_report,
        sample_cases_used=_extract_sample_cases(records),
        generation_success_count=success_count,
        generation_total_count=len(records),
        field_completeness=_calc_field_completeness(records),
        script_normalization_applied_count=_calc_normalization_applied(records),
        runtime_seconds=runtime_seconds,
    )


def _comparison_ready(current: ModelRunSummary, candidate: ModelRunSummary) -> bool:
    same_samples = set(current.sample_cases_used) == set(candidate.sample_cases_used)
    has_success = current.generation_success_count > 0 and candidate.generation_success_count > 0
    has_fields = any(current.field_completeness.values()) and any(candidate.field_completeness.values())
    return same_samples and has_success and has_fields


def _promotion_hint(current: ModelRunSummary, candidate: ModelRunSummary, comparison_ready: bool) -> str:
    if not comparison_ready:
        return "keep current default; rerun until comparison-ready is yes"

    candidate_not_worse = candidate.generation_success_count >= current.generation_success_count
    candidate_more_complete = sum(candidate.field_completeness.values()) >= sum(current.field_completeness.values())

    if candidate_not_worse and candidate_more_complete:
        return "candidate appears promotable; run final acceptance check then consider default switch"
    return "keep current default and expand sample batch for more evidence"


def _build_report(
    *,
    report_path: Path,
    current: ModelRunSummary,
    candidate: ModelRunSummary,
    sample_cases_used: list[str],
    comparison_ready: bool,
) -> str:
    promotion_hint = _promotion_hint(current, candidate, comparison_ready)

    lines = [
        "Re-benchmark Upgraded Local Model Candidate Report - Day 48",
        f"report_path: {report_path}",
        "",
        "=== Fixed Benchmark Conditions ===",
        f"current_model_name: {current.model_name}",
        f"candidate_model_name: {candidate.model_name}",
        f"prompt_version: {current.prompt_version}",
        f"sample cases used: {sample_cases_used}",
        f"sample_case_count: {len(sample_cases_used)}",
        "same_input_batch: yes",
        "same_generation_script: connect_local_chinese_model_metadata_generation.py",
        "same_normalization: Traditional Chinese normalization enabled",
        "same_timeout_and_input_truncation_policy: yes",
        "",
        "=== Current Model Results ===",
        f"generation success count: {current.generation_success_count}",
        f"generation total count: {current.generation_total_count}",
        f"field completeness: {current.field_completeness}",
        f"script normalization applied: {current.script_normalization_applied_count}",
        f"runtime seconds: {current.runtime_seconds:.2f}",
        "",
        "=== Candidate Model Results ===",
        f"generation success count: {candidate.generation_success_count}",
        f"generation total count: {candidate.generation_total_count}",
        f"field completeness: {candidate.field_completeness}",
        f"script normalization applied: {candidate.script_normalization_applied_count}",
        f"runtime seconds: {candidate.runtime_seconds:.2f}",
        "",
        "=== Decision Support ===",
        f"comparison-ready yes/no: {'yes' if comparison_ready else 'no'}",
        f"promotion hint: {promotion_hint}",
    ]

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Re-benchmark upgraded local model candidate (Day 48).")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--current-model-name", default=DEFAULT_CURRENT_MODEL)
    parser.add_argument("--candidate-model-name", default=DEFAULT_CANDIDATE_MODEL)
    parser.add_argument("--prompt-version", default=DEFAULT_PROMPT_VERSION)
    parser.add_argument("--backend", choices=["ollama_cli", "command"], default="ollama_cli")
    parser.add_argument("--command-template", default="", help="Used when --backend command.")
    parser.add_argument("--timeout-seconds", type=int, default=300)
    parser.add_argument("--sample-case-limit", type=int, default=10)
    parser.add_argument("--language", default="zh")
    parser.add_argument("--case-numbers", default="", help="Comma-separated authoritative case numbers.")
    parser.add_argument("--max-input-chars", type=int, default=8000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Input chunks file not found: {args.input}")

    args.output_dir.mkdir(parents=True, exist_ok=True)

    current_summary = _run_generation_once(
        input_path=args.input,
        output_dir=args.output_dir,
        model_name=args.current_model_name,
        prompt_version=args.prompt_version,
        backend=args.backend,
        command_template=args.command_template,
        timeout_seconds=args.timeout_seconds,
        sample_case_limit=args.sample_case_limit,
        language=args.language.strip().lower(),
        case_numbers=args.case_numbers,
        max_input_chars=args.max_input_chars,
        label="current",
    )

    fixed_case_numbers = ",".join(current_summary.sample_cases_used)
    candidate_summary = _run_generation_once(
        input_path=args.input,
        output_dir=args.output_dir,
        model_name=args.candidate_model_name,
        prompt_version=args.prompt_version,
        backend=args.backend,
        command_template=args.command_template,
        timeout_seconds=args.timeout_seconds,
        sample_case_limit=args.sample_case_limit,
        language=args.language.strip().lower(),
        case_numbers=fixed_case_numbers,
        max_input_chars=args.max_input_chars,
        label="candidate",
    )

    sample_cases = current_summary.sample_cases_used
    comparison_ready = _comparison_ready(current_summary, candidate_summary)
    promotion_hint = _promotion_hint(current_summary, candidate_summary, comparison_ready)

    report_text = _build_report(
        report_path=args.report,
        current=current_summary,
        candidate=candidate_summary,
        sample_cases_used=sample_cases,
        comparison_ready=comparison_ready,
    )

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report_text, encoding="utf-8")

    appears_successful = comparison_ready and "promotable" in promotion_hint

    print(f"current model tested: {current_summary.model_name}")
    print(f"candidate model tested: {candidate_summary.model_name}")
    print(f"prompt version fixed: {args.prompt_version}")
    print(f"sample cases processed: {len(sample_cases)}")
    print(f"current model successful generations: {current_summary.generation_success_count}")
    print(f"candidate model successful generations: {candidate_summary.generation_success_count}")
    print(f"whether upgraded local model re-benchmark appears successful: {appears_successful}")
    print(f"report written: {args.report}")

    return 0 if comparison_ready else 1


if __name__ == "__main__":
    raise SystemExit(main())
