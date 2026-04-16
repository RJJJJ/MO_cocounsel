#!/usr/bin/env python3
"""Day 38: build metadata-generation target schema for case-level legal research outputs.

Scope constraints:
- local-only
- no database
- no external API
- no LLM
- focus on target schema + sample shaped output
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
DEFAULT_REPORT_PATH = Path("data/eval/metadata_generation_target_schema_demo_report.txt")
DEFAULT_SAMPLE_CASE_LIMIT = 3


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
    return re.sub(r"\s+", " ", text).strip()


def deterministic_summary(text: str, max_chars: int = 260) -> str:
    cleaned = normalize_whitespace(text)
    if not cleaned:
        return ""
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3] + "..."


def extract_holding(text: str) -> str:
    cleaned = normalize_whitespace(text)
    if not cleaned:
        return ""

    sentence_candidates = re.split(r"(?<=[。.!?；;])", cleaned)
    keywords = ("裁定", "判決", "上訴", "駁回", "改判", "判處")
    for sentence in sentence_candidates:
        if any(keyword in sentence for keyword in keywords):
            return deterministic_summary(sentence, max_chars=180)
    return deterministic_summary(cleaned, max_chars=180)


def extract_legal_basis(text: str) -> list[str]:
    cleaned = normalize_whitespace(text)
    if not cleaned:
        return []

    # Deterministic draft: extract article-like mentions.
    matches = re.findall(r"第\s*\d+\s*條", cleaned)
    unique = []
    seen = set()
    for item in matches:
        normalized = item.replace(" ", "")
        if normalized in seen:
            continue
        seen.add(normalized)
        unique.append(normalized)
        if len(unique) >= 5:
            break
    return unique


def extract_disputed_issues(text: str, fallback_case_type: str) -> list[str]:
    cleaned = normalize_whitespace(text)
    if not cleaned:
        return [fallback_case_type] if fallback_case_type else []

    issue_match = re.search(r"主要問題[:：]\s*([^。]+)", cleaned)
    if issue_match:
        raw = issue_match.group(1)
        parts = [p.strip(" 、，,;；") for p in re.split(r"[、，,;；]", raw)]
        issues = [p for p in parts if p]
        if issues:
            return issues[:8]

    if fallback_case_type:
        return [fallback_case_type]
    return []


def build_case_metadata(case_chunks: list[CaseChunk]) -> dict[str, Any]:
    head = case_chunks[0]
    combined_text = " ".join(chunk.chunk_text for chunk in case_chunks)

    legal_basis = extract_legal_basis(combined_text)
    disputed_issues = extract_disputed_issues(combined_text, head.case_type)

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
            "case_summary": deterministic_summary(combined_text),
            "holding": extract_holding(combined_text),
            "legal_basis": legal_basis,
            "disputed_issues": disputed_issues,
        },
        "generation_status": "draft_schema_shaped_sample",
        "generation_method": "deterministic_local_extraction_placeholder",
        "provenance_notes": [
            "No LLM used.",
            "No external API/database used.",
            "Content is schema-shape demo for future metadata generation only.",
        ],
    }


def pick_sample_cases(grouped: dict[str, list[CaseChunk]], limit: int) -> list[tuple[str, list[CaseChunk]]]:
    ordered = sorted(grouped.items(), key=lambda item: item[0])
    return ordered[: max(limit, 1)]


def count_populated_fields(metadata_items: list[dict[str, Any]]) -> tuple[int, int]:
    populated = 0
    total = 0

    def walk(value: Any) -> None:
        nonlocal populated, total
        if isinstance(value, dict):
            for child in value.values():
                walk(child)
            return
        if isinstance(value, list):
            total += 1
            if value:
                populated += 1
            return

        total += 1
        if isinstance(value, str):
            if value.strip():
                populated += 1
            return
        if value is not None:
            populated += 1

    for item in metadata_items:
        walk(item)
    return populated, total


def build_report_lines(
    *,
    input_path: Path,
    sample_limit: int,
    selected_cases: list[tuple[str, list[CaseChunk]]],
    sample_outputs: list[dict[str, Any]],
) -> list[str]:
    populated, total = count_populated_fields(sample_outputs)
    success = bool(sample_outputs) and populated > 0

    lines = [
        "Metadata Generation Target Schema Demo Report - Day 38",
        f"input_chunks_path: {input_path}",
        f"sample_case_limit: {sample_limit}",
        f"sample cases processed: {len(selected_cases)}",
        f"sample case numbers: {[case_number for case_number, _ in selected_cases]}",
        f"target fields populated count: {populated}/{total}",
        f"metadata-generation target schema build appears successful: {success}",
        "",
        "Schema shape notes:",
        "- core_case_metadata defines authoritative case-level fields and source traceability anchors.",
        "- generated_digest_metadata fields are deterministic placeholders in this round.",
        "- No claim of high-quality metadata generation in this round.",
        "",
        "Sample shaped outputs:",
    ]

    for idx, item in enumerate(sample_outputs, start=1):
        lines.append(f"\n=== sample_case_{idx} ===")
        lines.append(json.dumps(item, ensure_ascii=False, indent=2))

    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Day 38 metadata generation target schema demo output.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH, help="Input bm25 chunks jsonl path")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH, help="Output report txt path")
    parser.add_argument("--sample-case-limit", type=int, default=DEFAULT_SAMPLE_CASE_LIMIT, help="Number of sample cases")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Input chunks file not found: {args.input}")

    chunks = load_chunks(args.input)
    grouped = group_chunks_by_case(chunks)
    selected = pick_sample_cases(grouped, args.sample_case_limit)
    sample_outputs = [build_case_metadata(case_chunks) for _, case_chunks in selected]

    lines = build_report_lines(
        input_path=args.input,
        sample_limit=args.sample_case_limit,
        selected_cases=selected,
        sample_outputs=sample_outputs,
    )

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Required terminal summary lines
    print(f"sample cases processed: {len(selected)}")
    populated, total = count_populated_fields(sample_outputs)
    print(f"target fields populated count: {populated}/{total}")
    print(
        "whether metadata-generation target schema build appears successful: "
        f"{bool(sample_outputs) and populated > 0}"
    )
    print(f"report written: {args.report}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
