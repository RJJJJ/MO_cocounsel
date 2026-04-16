#!/usr/bin/env python3
"""Day 40: local metadata field evaluation runner for deterministic baseline.

Scope constraints:
- local-only
- no database
- no external API
- no LLM

Compares a curated evaluation set against deterministic metadata output.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_EVAL_SET_PATH = Path("data/eval/metadata_field_evaluation_set.jsonl")
DEFAULT_PREDICTION_PATH = Path("data/eval/deterministic_metadata_extraction_baseline_output.jsonl")
DEFAULT_REPORT_PATH = Path("data/eval/metadata_field_evaluation_report.txt")


@dataclass(frozen=True)
class FieldScore:
    exact: float
    normalized: float


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file_obj:
        for line_no, line in enumerate(file_obj, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at {path}:{line_no}: {exc}") from exc
    return rows


def normalize_text(value: str) -> str:
    cleaned = value.strip().lower()
    cleaned = cleaned.replace("\u3000", " ")
    cleaned = re.sub(r"\s+", " ", cleaned)
    cleaned = re.sub(r"[\*\-_,.;:!?'\"()\[\]{}]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def text_tokens(value: str) -> set[str]:
    normalized = normalize_text(value)
    if not normalized:
        return set()
    return set(re.findall(r"[a-z0-9\u4e00-\u9fff]+", normalized, flags=re.IGNORECASE))


def list_exact_score(expected: list[str], predicted: list[str]) -> float:
    return 1.0 if expected == predicted else 0.0


def list_normalized_overlap(expected: list[str], predicted: list[str]) -> float:
    exp = {normalize_text(item) for item in expected if normalize_text(item)}
    pred = {normalize_text(item) for item in predicted if normalize_text(item)}
    if not exp and not pred:
        return 1.0
    if not exp:
        return 0.0
    intersection = len(exp & pred)
    return intersection / max(len(exp), 1)


def loose_text_overlap(expected: str, predicted: str) -> float:
    exp_tokens = text_tokens(expected)
    pred_tokens = text_tokens(predicted)
    if not exp_tokens and not pred_tokens:
        return 1.0
    if not exp_tokens:
        return 0.0
    intersection = len(exp_tokens & pred_tokens)
    return intersection / max(len(exp_tokens), 1)


def containment_signal(expected: str, predicted: str) -> float:
    exp = normalize_text(expected)
    pred = normalize_text(predicted)
    if not exp and not pred:
        return 1.0
    if not exp or not pred:
        return 0.0
    return 1.0 if (exp in pred or pred in exp) else 0.0


def mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run metadata field evaluation (Day 40).")
    parser.add_argument("--eval-set", type=Path, default=DEFAULT_EVAL_SET_PATH, help="Evaluation set JSONL")
    parser.add_argument("--predictions", type=Path, default=DEFAULT_PREDICTION_PATH, help="Deterministic baseline output JSONL")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH, help="Output report path")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.eval_set.exists():
        raise FileNotFoundError(f"Evaluation set file not found: {args.eval_set}")
    if not args.predictions.exists():
        raise FileNotFoundError(f"Prediction file not found: {args.predictions}")

    eval_rows = load_jsonl(args.eval_set)
    prediction_rows = load_jsonl(args.predictions)

    predicted_by_case: dict[str, dict[str, Any]] = {}
    for row in prediction_rows:
        case_number = str(row.get("core_case_metadata", {}).get("authoritative_case_number", "")).strip()
        if case_number:
            predicted_by_case[case_number] = row

    case_summary_overlap_scores: list[float] = []
    case_summary_containment_scores: list[float] = []
    holding_overlap_scores: list[float] = []
    holding_containment_scores: list[float] = []
    legal_exact_scores: list[float] = []
    legal_norm_scores: list[float] = []
    issues_exact_scores: list[float] = []
    issues_norm_scores: list[float] = []

    per_field_populated = {
        "case_summary": 0,
        "holding": 0,
        "legal_basis": 0,
        "disputed_issues": 0,
    }

    missing_cases: list[str] = []

    for expected in eval_rows:
        case_number = str(expected.get("authoritative_case_number", "")).strip()
        if not case_number or case_number not in predicted_by_case:
            missing_cases.append(case_number or "<empty_case_number>")
            continue

        predicted = predicted_by_case[case_number].get("generated_digest_metadata", {})

        expected_summary = str(expected.get("expected_case_summary", ""))
        predicted_summary = str(predicted.get("case_summary", ""))
        expected_holding = str(expected.get("expected_holding", ""))
        predicted_holding = str(predicted.get("holding", ""))
        expected_legal = [str(item) for item in expected.get("expected_legal_basis", [])]
        predicted_legal = [str(item) for item in predicted.get("legal_basis", [])]
        expected_issues = [str(item) for item in expected.get("expected_disputed_issues", [])]
        predicted_issues = [str(item) for item in predicted.get("disputed_issues", [])]

        if normalize_text(predicted_summary):
            per_field_populated["case_summary"] += 1
        if normalize_text(predicted_holding):
            per_field_populated["holding"] += 1
        if predicted_legal:
            per_field_populated["legal_basis"] += 1
        if predicted_issues:
            per_field_populated["disputed_issues"] += 1

        case_summary_overlap_scores.append(loose_text_overlap(expected_summary, predicted_summary))
        case_summary_containment_scores.append(containment_signal(expected_summary, predicted_summary))
        holding_overlap_scores.append(loose_text_overlap(expected_holding, predicted_holding))
        holding_containment_scores.append(containment_signal(expected_holding, predicted_holding))

        legal_exact_scores.append(list_exact_score(expected_legal, predicted_legal))
        legal_norm_scores.append(list_normalized_overlap(expected_legal, predicted_legal))

        issues_exact_scores.append(list_exact_score(expected_issues, predicted_issues))
        issues_norm_scores.append(list_normalized_overlap(expected_issues, predicted_issues))

    evaluated_count = len(eval_rows) - len(missing_cases)
    total_count = len(eval_rows)

    coverage = {
        field: (per_field_populated[field] / evaluated_count if evaluated_count else 0.0)
        for field in per_field_populated
    }

    case_summary_score = {
        "overlap_avg": mean(case_summary_overlap_scores),
        "containment_avg": mean(case_summary_containment_scores),
    }
    holding_score = {
        "overlap_avg": mean(holding_overlap_scores),
        "containment_avg": mean(holding_containment_scores),
    }
    legal_basis_score = {
        "exact_avg": mean(legal_exact_scores),
        "normalized_overlap_avg": mean(legal_norm_scores),
    }
    disputed_issues_score = {
        "exact_avg": mean(issues_exact_scores),
        "normalized_overlap_avg": mean(issues_norm_scores),
    }

    field_quality = {
        "case_summary": case_summary_score["overlap_avg"],
        "holding": holding_score["overlap_avg"],
        "legal_basis": legal_basis_score["normalized_overlap_avg"],
        "disputed_issues": disputed_issues_score["normalized_overlap_avg"],
    }
    weakest_field = min(field_quality.items(), key=lambda item: item[1])[0] if field_quality else "n/a"

    appears_successful = (
        evaluated_count >= max(1, total_count // 2)
        and all(score >= 0.75 for score in coverage.values())
        and case_summary_score["overlap_avg"] >= 0.20
        and holding_score["overlap_avg"] >= 0.20
        and legal_basis_score["normalized_overlap_avg"] >= 0.40
        and disputed_issues_score["normalized_overlap_avg"] >= 0.40
    )

    report_lines = [
        "Metadata Field Evaluation Report - Day 40",
        f"evaluation_set_path: {args.eval_set}",
        f"predictions_path: {args.predictions}",
        f"cases in set: {total_count}",
        f"cases evaluated: {evaluated_count}",
        f"cases missing predictions: {len(missing_cases)}",
        f"missing case numbers: {', '.join(missing_cases) if missing_cases else 'none'}",
        "",
        "Field coverage:",
        f"- case_summary: {coverage['case_summary']:.3f}",
        f"- holding: {coverage['holding']:.3f}",
        f"- legal_basis: {coverage['legal_basis']:.3f}",
        f"- disputed_issues: {coverage['disputed_issues']:.3f}",
        "",
        "case_summary score summary:",
        f"- loose_text_overlap_avg: {case_summary_score['overlap_avg']:.3f}",
        f"- containment_signal_avg: {case_summary_score['containment_avg']:.3f}",
        "",
        "holding score summary:",
        f"- loose_text_overlap_avg: {holding_score['overlap_avg']:.3f}",
        f"- containment_signal_avg: {holding_score['containment_avg']:.3f}",
        "",
        "legal_basis score summary:",
        f"- exact_match_avg: {legal_basis_score['exact_avg']:.3f}",
        f"- normalized_overlap_avg: {legal_basis_score['normalized_overlap_avg']:.3f}",
        "",
        "disputed_issues score summary:",
        f"- exact_match_avg: {disputed_issues_score['exact_avg']:.3f}",
        f"- normalized_overlap_avg: {disputed_issues_score['normalized_overlap_avg']:.3f}",
        "",
        f"weakest field: {weakest_field}",
        f"whether metadata field evaluation appears successful: {appears_successful}",
    ]

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"cases evaluated: {evaluated_count}/{total_count}")
    print(f"case_summary score summary: overlap_avg={case_summary_score['overlap_avg']:.3f}, containment_avg={case_summary_score['containment_avg']:.3f}")
    print(f"holding score summary: overlap_avg={holding_score['overlap_avg']:.3f}, containment_avg={holding_score['containment_avg']:.3f}")
    print(f"legal_basis score summary: exact_avg={legal_basis_score['exact_avg']:.3f}, normalized_overlap_avg={legal_basis_score['normalized_overlap_avg']:.3f}")
    print(f"disputed_issues score summary: exact_avg={disputed_issues_score['exact_avg']:.3f}, normalized_overlap_avg={disputed_issues_score['normalized_overlap_avg']:.3f}")
    print(f"weakest field: {weakest_field}")
    print(f"whether metadata field evaluation appears successful: {appears_successful}")
    print(f"report written: {args.report}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
