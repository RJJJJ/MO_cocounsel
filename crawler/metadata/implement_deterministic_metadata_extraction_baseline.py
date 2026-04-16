#!/usr/bin/env python3
"""Day 39: deterministic metadata extraction baseline for case-level digest fields.

Scope constraints:
- local-only
- no database
- no external API
- no LLM

This script reads prepared corpus chunks and emits reproducible case-level metadata
using simple language-aware heuristics (zh / pt) with explicit fallbacks.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_INPUT_PATH = Path("data/corpus/prepared/macau_court_cases/bm25_chunks.jsonl")
DEFAULT_OUTPUT_PATH = Path("data/eval/deterministic_metadata_extraction_baseline_output.jsonl")
DEFAULT_REPORT_PATH = Path("data/eval/deterministic_metadata_extraction_baseline_report.txt")
DEFAULT_SAMPLE_CASES_IN_REPORT = 3


@dataclass(frozen=True)
class CaseChunk:
    chunk_id: str
    authoritative_case_number: str
    authoritative_decision_date: str
    court: str
    language: str
    case_type: str
    pdf_url: str
    text_url_or_action: str
    source_metadata_path: str
    source_full_text_path: str
    chunk_text: str


def load_chunks(path: Path) -> list[CaseChunk]:
    chunks: list[CaseChunk] = []
    with path.open("r", encoding="utf-8") as file_obj:
        for line_no, line in enumerate(file_obj, start=1):
            line = line.strip()
            if not line:
                continue
            payload = json.loads(line)
            try:
                chunks.append(
                    CaseChunk(
                        chunk_id=str(payload.get("chunk_id", "")),
                        authoritative_case_number=str(payload.get("authoritative_case_number", "")),
                        authoritative_decision_date=str(payload.get("authoritative_decision_date", "")),
                        court=str(payload.get("court", "")),
                        language=str(payload.get("language", "")),
                        case_type=str(payload.get("case_type", "")),
                        pdf_url=str(payload.get("pdf_url", "")),
                        text_url_or_action=str(payload.get("text_url_or_action", "")),
                        source_metadata_path=str(payload.get("source_metadata_path", "")),
                        source_full_text_path=str(payload.get("source_full_text_path", "")),
                        chunk_text=str(payload.get("chunk_text", "")),
                    )
                )
            except Exception as exc:  # pragma: no cover - defensive local guard
                raise ValueError(f"Invalid row at line {line_no}: {exc}") from exc
    return chunks


def group_chunks_by_case(chunks: list[CaseChunk]) -> dict[str, list[CaseChunk]]:
    grouped: dict[str, list[CaseChunk]] = defaultdict(list)
    for chunk in chunks:
        case_number = chunk.authoritative_case_number or "UNKNOWN_CASE"
        grouped[case_number].append(chunk)
    return dict(grouped)


def normalize_whitespace(text: str) -> str:
    text = text.replace("\u3000", " ")
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text: str) -> list[str]:
    if not text:
        return []
    pieces = re.split(r"(?<=[。.!?；;])\s+", text)
    return [p.strip() for p in pieces if p.strip()]


def clip(text: str, max_chars: int) -> str:
    cleaned = normalize_whitespace(text)
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3] + "..."


def extract_heading_block(text: str, heading_patterns: list[str], stop_patterns: list[str]) -> str:
    if not text:
        return ""
    heading_regex = "|".join(heading_patterns)
    stop_regex = "|".join(stop_patterns)
    pattern = re.compile(
        rf"(?:{heading_regex})\s*[:：]?\s*(.+?)(?=(?:{stop_regex})\s*[:：]?|$)",
        flags=re.IGNORECASE | re.DOTALL,
    )
    match = pattern.search(text)
    if not match:
        return ""
    return normalize_whitespace(match.group(1))


def extract_case_summary(language: str, text: str) -> str:
    cleaned = normalize_whitespace(text)
    if not cleaned:
        return ""

    if language == "zh":
        block = extract_heading_block(
            cleaned,
            heading_patterns=[r"摘要", r"案情摘要"],
            stop_patterns=[r"裁判", r"決定", r"理由說明", r"事實", r"法律依據"],
        )
        if block:
            return clip(block, 280)
    elif language == "pt":
        block = extract_heading_block(
            cleaned,
            heading_patterns=[r"SUM[ÁA]RIO", r"RESUMO"],
            stop_patterns=[r"DECIS[ÃA]O", r"FUNDAMENTA[CÇ][ÃA]O", r"ACORDAM", r"RELAT[ÓO]RIO"],
        )
        if block:
            return clip(block, 280)

    sentences = split_sentences(cleaned)
    if not sentences:
        return ""
    return clip(" ".join(sentences[:2]), 280)


def extract_holding(language: str, text: str) -> str:
    cleaned = normalize_whitespace(text)
    if not cleaned:
        return ""

    sentences = split_sentences(cleaned)
    if not sentences:
        return ""

    if language == "zh":
        keywords = ["裁定", "判決", "決定", "駁回", "改判", "判處", "維持原判", "上訴理由不成立"]
    else:
        keywords = [
            "acordam",
            "decisão",
            "decidem",
            "julgar",
            "negar provimento",
            "conceder provimento",
            "improcedente",
            "procedente",
            "condenar",
            "absolver",
        ]

    matched = [sentence for sentence in sentences if any(k.lower() in sentence.lower() for k in keywords)]
    if matched:
        # Prefer terminal operative sentence.
        return clip(matched[-1], 220)

    # Fallback: use final sentence as deterministic proxy.
    return clip(sentences[-1], 220)


def extract_legal_basis(language: str, text: str) -> list[str]:
    cleaned = normalize_whitespace(text)
    if not cleaned:
        return []

    if language == "zh":
        raw_matches = re.findall(r"第\s*\d+\s*(?:之\s*\d+)?\s*條", cleaned)
        normalized = [re.sub(r"\s+", "", item) for item in raw_matches]
    else:
        raw_matches = re.findall(r"art(?:igo|\.)?\s*\d+[.º°o]*", cleaned, flags=re.IGNORECASE)
        normalized = [re.sub(r"\s+", " ", item).strip() for item in raw_matches]

    uniq: list[str] = []
    seen: set[str] = set()
    for item in normalized:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(item)
        if len(uniq) >= 8:
            break
    return uniq


def split_issue_candidates(raw: str) -> list[str]:
    candidates = re.split(r"[、，,;；]+", raw)
    return [normalize_whitespace(item).strip("-:：") for item in candidates if normalize_whitespace(item)]


def extract_disputed_issues(language: str, text: str, case_type: str) -> list[str]:
    cleaned = normalize_whitespace(text)
    if not cleaned:
        return [case_type] if case_type else []

    patterns: list[str]
    if language == "zh":
        patterns = [r"主要問題\s*[:：]\s*([^。]+)", r"爭議焦點\s*[:：]\s*([^。]+)"]
    else:
        patterns = [r"Assunto\s*[:：]\s*([^\.]+)", r"Quest[õo]es\s*[:：]\s*([^\.]+)"]

    for pattern in patterns:
        match = re.search(pattern, cleaned, flags=re.IGNORECASE)
        if not match:
            continue
        issues = split_issue_candidates(match.group(1))
        if issues:
            return issues[:8]

    return [case_type] if case_type else []


def build_case_metadata(case_chunks: list[CaseChunk]) -> dict[str, Any]:
    head = case_chunks[0]
    combined_text = normalize_whitespace(" ".join(chunk.chunk_text for chunk in case_chunks))

    summary = extract_case_summary(head.language, combined_text)
    holding = extract_holding(head.language, combined_text)
    legal_basis = extract_legal_basis(head.language, combined_text)
    disputed_issues = extract_disputed_issues(head.language, combined_text, head.case_type)

    return {
        "core_case_metadata": {
            "authoritative_case_number": head.authoritative_case_number,
            "authoritative_decision_date": head.authoritative_decision_date,
            "court": head.court,
            "language": head.language,
            "case_type": head.case_type,
            "pdf_url": head.pdf_url,
            "text_url_or_action": head.text_url_or_action,
            "source_chunk_ids": [chunk.chunk_id for chunk in case_chunks],
            "source_case_paths": sorted(
                {
                    path
                    for path in [head.source_metadata_path, head.source_full_text_path]
                    if path
                }
            ),
        },
        "generated_digest_metadata": {
            "case_summary": summary,
            "holding": holding,
            "legal_basis": legal_basis,
            "disputed_issues": disputed_issues,
        },
        "generation_status": "deterministic_baseline",
        "generation_method": "deterministic_rule_based_extraction_local_only",
        "provenance_notes": [
            "No LLM used.",
            "No external API/database used.",
            "Heuristic extraction only; quality is baseline-level.",
        ],
    }


def is_populated(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return len(value) > 0
    return value is not None


def compute_field_population_stats(items: list[dict[str, Any]]) -> dict[str, int]:
    fields = ["case_summary", "holding", "legal_basis", "disputed_issues"]
    stats = {"cases_processed": len(items)}
    for field in fields:
        stats[f"{field}_populated"] = sum(
            1
            for item in items
            if is_populated(item.get("generated_digest_metadata", {}).get(field))
        )
    return stats


def write_jsonl(path: Path, items: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_obj:
        for item in items:
            file_obj.write(json.dumps(item, ensure_ascii=False) + "\n")


def build_report_lines(
    *,
    input_path: Path,
    output_path: Path,
    stats: dict[str, int],
    sample_items: list[dict[str, Any]],
) -> list[str]:
    cases_processed = stats["cases_processed"]
    success = (
        cases_processed > 0
        and stats["case_summary_populated"] > 0
        and stats["holding_populated"] > 0
        and stats["legal_basis_populated"] > 0
        and stats["disputed_issues_populated"] > 0
    )

    lines = [
        "Deterministic Metadata Extraction Baseline Report - Day 39",
        f"input_chunks_path: {input_path}",
        f"output_jsonl_path: {output_path}",
        f"cases processed: {cases_processed}",
        f"case_summary populated: {stats['case_summary_populated']}",
        f"holding populated: {stats['holding_populated']}",
        f"legal_basis populated: {stats['legal_basis_populated']}",
        f"disputed_issues populated: {stats['disputed_issues_populated']}",
        f"whether deterministic metadata extraction baseline appears successful: {success}",
        "",
        "Notes:",
        "- Baseline is deterministic and heuristic-only.",
        "- zh/pt use different extraction patterns.",
        "- Empty/fallback handling is explicit for all required digest fields.",
        "",
        "Sample shaped metadata outputs:",
    ]

    for idx, item in enumerate(sample_items, start=1):
        lines.append(f"\n=== sample_case_{idx} ===")
        lines.append(json.dumps(item, ensure_ascii=False, indent=2))

    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Implement deterministic metadata extraction baseline (Day 39).")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH, help="Input bm25 chunks jsonl path")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Per-case shaped metadata output jsonl path")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH, help="Output report txt path")
    parser.add_argument(
        "--sample-cases-in-report",
        type=int,
        default=DEFAULT_SAMPLE_CASES_IN_REPORT,
        help="How many sample cases to include in report",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Input chunks file not found: {args.input}")

    chunks = load_chunks(args.input)
    grouped = group_chunks_by_case(chunks)

    all_items: list[dict[str, Any]] = []
    for case_number in sorted(grouped.keys()):
        case_chunks = grouped[case_number]
        all_items.append(build_case_metadata(case_chunks))

    write_jsonl(args.output, all_items)

    stats = compute_field_population_stats(all_items)
    sample_count = max(args.sample_cases_in_report, 0)
    sample_items = all_items[:sample_count]
    report_lines = build_report_lines(
        input_path=args.input,
        output_path=args.output,
        stats=stats,
        sample_items=sample_items,
    )

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    success = (
        stats["cases_processed"] > 0
        and stats["case_summary_populated"] > 0
        and stats["holding_populated"] > 0
        and stats["legal_basis_populated"] > 0
        and stats["disputed_issues_populated"] > 0
    )

    # Required terminal output summary lines
    print(f"cases processed: {stats['cases_processed']}")
    print(f"case_summary populated: {stats['case_summary_populated']}")
    print(f"holding populated: {stats['holding_populated']}")
    print(f"legal_basis populated: {stats['legal_basis_populated']}")
    print(f"disputed_issues populated: {stats['disputed_issues_populated']}")
    print(f"whether deterministic metadata extraction baseline appears successful: {success}")
    print(f"output written: {args.output}")
    print(f"report written: {args.report}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
