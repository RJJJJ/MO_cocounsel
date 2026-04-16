#!/usr/bin/env python3
"""Day 42: metadata generation comparison harness.

Compares deterministic baseline metadata against future local-model-generated metadata
for selected digest fields.

Scope constraints:
- local-only
- no database
- no external API
- no cloud model integration
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_BASELINE_PATH = Path("data/eval/deterministic_metadata_extraction_baseline_output.jsonl")
DEFAULT_MODEL_PATH = Path("data/eval/model_generated_metadata_output.jsonl")
DEFAULT_REPORT_PATH = Path("data/eval/metadata_generation_comparison_harness_report.txt")

COMPARED_FIELDS = ["case_summary", "holding", "legal_basis", "disputed_issues"]


@dataclass(frozen=True)
class CaseMetadataRecord:
    authoritative_case_number: str
    language: str
    fields: dict[str, Any]


def _normalize_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " | ".join(str(item).strip() for item in value if str(item).strip())
    return str(value).strip()


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


def _extract_record(payload: dict[str, Any]) -> CaseMetadataRecord:
    core = payload.get("core_case_metadata") or {}
    generated = payload.get("generated_digest_metadata") or {}

    case_number = str(
        core.get("authoritative_case_number")
        or payload.get("authoritative_case_number")
        or payload.get("case_number")
        or "UNKNOWN_CASE"
    )
    language = str(core.get("language") or payload.get("language") or "unknown")

    fields: dict[str, Any] = {}
    for field in COMPARED_FIELDS:
        if field in generated:
            fields[field] = generated.get(field)
        else:
            fields[field] = payload.get(field)

    return CaseMetadataRecord(
        authoritative_case_number=case_number,
        language=language,
        fields=fields,
    )


def load_case_metadata(path: Path) -> dict[str, CaseMetadataRecord]:
    records: dict[str, CaseMetadataRecord] = {}
    for payload in _load_jsonl(path):
        record = _extract_record(payload)
        records[record.authoritative_case_number] = record
    return records


def compare_case(
    baseline: CaseMetadataRecord,
    model: CaseMetadataRecord | None,
) -> tuple[list[dict[str, str]], int]:
    comparisons: list[dict[str, str]] = []
    missing_fields = 0

    for field in COMPARED_FIELDS:
        baseline_value = _normalize_value(baseline.fields.get(field))
        model_value = _normalize_value(model.fields.get(field)) if model else ""

        if not model:
            status = "model_pending"
            missing_fields += 1
        elif not model_value:
            status = "model_missing_field"
            missing_fields += 1
        elif not baseline_value:
            status = "baseline_missing_field"
        elif baseline_value == model_value:
            status = "match"
        else:
            status = "different"

        comparisons.append(
            {
                "field": field,
                "baseline_value": baseline_value,
                "model_value": model_value,
                "comparison_status": status,
            }
        )

    return comparisons, missing_fields


def build_report_lines(
    baseline_records: dict[str, CaseMetadataRecord],
    model_records: dict[str, CaseMetadataRecord],
) -> tuple[list[str], dict[str, Any]]:
    baseline_cases = len(baseline_records)
    model_cases = len(model_records)

    model_missing_case_count = 0
    model_missing_field_count = 0
    cases_with_model = 0

    lines: list[str] = [
        "Metadata Generation Comparison Harness Report - Day 42",
        "",
        f"baseline cases loaded: {baseline_cases}",
        f"model-generated cases loaded: {model_cases}",
        "",
    ]

    for case_number in sorted(baseline_records):
        baseline = baseline_records[case_number]
        model = model_records.get(case_number)
        if model:
            cases_with_model += 1
        else:
            model_missing_case_count += 1

        comparisons, missing_fields = compare_case(baseline=baseline, model=model)
        model_missing_field_count += missing_fields

        lines.append(f"case: {baseline.authoritative_case_number}")
        lines.append(f"language: {baseline.language}")
        for row in comparisons:
            lines.append(f"- field: {row['field']}")
            lines.append(f"  baseline_value: {row['baseline_value'] or '<empty>'}")
            lines.append(f"  model_value: {row['model_value'] or '<empty>'}")
            lines.append(f"  comparison_status: {row['comparison_status']}")
        lines.append("")

    comparable_cases = cases_with_model
    fields_compared = baseline_cases * len(COMPARED_FIELDS)
    comparison_ready = comparable_cases > 0 and model_missing_field_count < fields_compared

    lines.extend(
        [
            "=== Aggregated Summary ===",
            f"cases compared: {comparable_cases}",
            f"fields compared: {fields_compared}",
            f"fields where model is missing: {model_missing_field_count}",
            f"model-missing case count: {model_missing_case_count}",
            f"comparison-ready: {'yes' if comparison_ready else 'no'}",
        ]
    )

    if model_cases == 0:
        lines.extend(
            [
                "",
                "placeholder mode status:",
                "- baseline available: yes",
                "- model-generated layer pending: yes",
            ]
        )

    summary = {
        "baseline_cases_loaded": baseline_cases,
        "model_generated_cases_loaded": model_cases,
        "comparable_cases_count": comparable_cases,
        "model_missing_count": model_missing_field_count,
        "comparison_ready": comparison_ready,
    }
    return lines, summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build metadata generation comparison harness (Day 42).")
    parser.add_argument("--baseline-input", type=Path, default=DEFAULT_BASELINE_PATH)
    parser.add_argument("--model-input", type=Path, default=DEFAULT_MODEL_PATH)
    parser.add_argument("--report-output", type=Path, default=DEFAULT_REPORT_PATH)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.baseline_input.exists():
        raise FileNotFoundError(
            f"Baseline input not found: {args.baseline_input}. "
            "Run deterministic metadata baseline first or pass --baseline-input."
        )

    baseline_records = load_case_metadata(args.baseline_input)
    model_records = load_case_metadata(args.model_input) if args.model_input.exists() else {}

    lines, summary = build_report_lines(baseline_records=baseline_records, model_records=model_records)

    args.report_output.parent.mkdir(parents=True, exist_ok=True)
    args.report_output.write_text("\n".join(lines) + "\n", encoding="utf-8")

    success = summary["baseline_cases_loaded"] > 0
    print(f"baseline cases loaded: {summary['baseline_cases_loaded']}")
    print(f"model-generated cases loaded: {summary['model_generated_cases_loaded']}")
    print(f"comparable cases count: {summary['comparable_cases_count']}")
    print(f"model-missing count: {summary['model_missing_count']}")
    print(f"whether metadata generation comparison harness appears successful: {success}")
    print(f"report written to: {args.report_output}")

    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
