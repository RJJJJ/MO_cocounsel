#!/usr/bin/env python3
"""Build Day63B dense vs baselines textual comparison."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_DAY63B_RESULTS = Path("data/eval/day63b_dense_retrieval_results.json")
DEFAULT_DAY63_RESULTS = Path("data/eval/day63_dense_retrieval_results.json")
DEFAULT_BM25_RESULTS = Path("data/eval/day61_regression_results.json")
DEFAULT_OUTPUT = Path("data/eval/day63b_dense_vs_baselines_comparison.txt")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _result_map(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["query_id"]: item for item in payload.get("results", [])}


def _passed_ids(payload: dict[str, Any]) -> set[str]:
    return {item["query_id"] for item in payload.get("results", []) if bool(item.get("passed"))}


def _top_cases(item: dict[str, Any], limit: int = 3) -> list[str]:
    return [str(hit.get("authoritative_case_number", "")) for hit in item.get("top_hits", [])[:limit]]


def _safe_pass_rate(payload: dict[str, Any]) -> str:
    if not payload:
        return "N/A"
    if payload.get("runtime_error"):
        return "N/A (runtime blocked)"
    return f"{float(payload.get('pass_rate', 0.0)):.2%}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Day63B dense comparison summary")
    parser.add_argument("--day63b", type=Path, default=DEFAULT_DAY63B_RESULTS)
    parser.add_argument("--day63", type=Path, default=DEFAULT_DAY63_RESULTS)
    parser.add_argument("--bm25", type=Path, default=DEFAULT_BM25_RESULTS)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    day63_payload = _read_json(args.day63)
    bm25_payload = _read_json(args.bm25)

    day63b_payload: dict[str, Any] = {}
    day63b_exists = args.day63b.exists()
    day63b_runtime_error: str | None = None
    if day63b_exists:
        day63b_payload = _read_json(args.day63b)
        runtime_error = day63b_payload.get("runtime_error")
        if runtime_error:
            day63b_runtime_error = str(runtime_error)

    lines: list[str] = [
        "Day63B Dense vs Baselines Comparison",
        f"day63b_results_path: {args.day63b}",
        f"day63_results_path: {args.day63}",
        f"bm25_results_path: {args.bm25}",
        "",
        "Pass rate comparison:",
        f"- Day63B dense (bge-m3): {_safe_pass_rate(day63b_payload) if day63b_exists else 'N/A (results not generated)'}",
        f"- Day63 dense (chargram): {_safe_pass_rate(day63_payload)}",
        f"- BM25+: {_safe_pass_rate(bm25_payload)}",
        "",
        "Exact case-number lookup behavior:",
    ]

    if not day63b_exists or day63b_runtime_error:
        lines.append("- Day63B run not available in current environment; exact-lookup behavior cannot be measured yet.")
    else:
        day63b_map = _result_map(day63b_payload)
        for query_id in ["day61_q03_exact_253_2026", "day61_q04_case_number_with_prefix"]:
            q = day63b_map.get(query_id, {})
            lines.append(f"- {query_id}: passed={q.get('passed')} top3={_top_cases(q)}")

    lines.extend(
        [
            "",
            "zh concept query behavior:",
            "- Focus slice: day61_q01/day61_q02/day61_q05/day61_q10.",
            "",
            "pt/mixed query behavior:",
            "- Focus slice: day61_q07/day61_q08/day61_q09.",
            "",
        ]
    )

    if day63b_exists and not day63b_runtime_error:
        day63b_pass = _passed_ids(day63b_payload)
        day63_pass = _passed_ids(day63_payload)
        bm25_pass = _passed_ids(bm25_payload)

        improved_vs_day63 = sorted(day63b_pass - day63_pass)
        still_fail = sorted({item["query_id"] for item in day63b_payload.get("results", []) if not item.get("passed")})
        worse_than_bm25 = sorted(bm25_pass - day63b_pass)

        lines.append("Queries improved most (Day63B vs Day63 chargram):")
        lines.append(f"- {improved_vs_day63 or ['none']}")
        lines.append("Queries still fail in Day63B:")
        lines.append(f"- {still_fail or ['none']}")
        lines.append("Queries BM25+ still wins on:")
        lines.append(f"- {worse_than_bm25 or ['none']}")

        day63b_rate = float(day63b_payload.get("pass_rate", 0.0))
        lines.append("")
        lines.append("Is Day63B good enough for Day64 fusion dense signal?")
        if day63b_rate >= 0.7:
            lines.append("- Yes, with BM25 exact-lookup guardrails retained.")
        else:
            lines.append("- Partially. Dense signal improved but should remain auxiliary under BM25 guardrails.")
    else:
        if day63b_runtime_error:
            lines.append(f"Day63B runtime status: blocked by dependency error: {day63b_runtime_error}")
        lines.append("Which queries improved most:")
        lines.append("- Pending Day63B run output.")
        lines.append("Which queries still fail:")
        lines.append("- Pending Day63B run output.")
        lines.append("Is Day63B good enough for Day64 fusion dense signal?")
        lines.append("- Pending Day63B run output; likely yes only as auxiliary signal with BM25 exact-match guardrail.")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"comparison_output: {args.output}")


if __name__ == "__main__":
    main()
