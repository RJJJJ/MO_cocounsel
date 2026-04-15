#!/usr/bin/env python3
"""Build a normalized raw corpus layout from Day 18 selector-card text details."""

from __future__ import annotations

import json
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

INPUT_PATH = Path("data/parsed/court_probe/playwright_text_details_from_selector_cards.jsonl")
OUTPUT_ROOT = Path("data/corpus/raw/macau_court_cases")
CASES_ROOT = OUTPUT_ROOT / "cases"
MANIFEST_PATH = OUTPUT_ROOT / "manifest.jsonl"
REPORT_PATH = OUTPUT_ROOT / "raw_corpus_build_report.txt"
EXTRACTION_SOURCE = "day18_selector_card_batch"


@dataclass
class BuildStats:
    total_records_read: int = 0
    total_corpus_records_written: int = 0
    zh_records_written: int = 0
    pt_records_written: int = 0
    records_with_authoritative_case_number: int = 0
    records_with_authoritative_decision_date: int = 0


def normalize_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def choose_authoritative(record: dict[str, Any], detail_key: str, source_key: str) -> str:
    detail_value = normalize_text(record.get(detail_key))
    if detail_value:
        return detail_value
    return normalize_text(record.get(source_key))


def extract_year(authoritative_decision_date: str, fallback_year: str = "unknown_year") -> str:
    if not authoritative_decision_date:
        return fallback_year
    match = re.search(r"(19|20)\d{2}", authoritative_decision_date)
    if match:
        return match.group(0)
    return fallback_year


def slugify_case_number(case_number: str, index: int) -> str:
    cleaned = normalize_text(case_number).lower()
    cleaned = re.sub(r"[^0-9a-z]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    if cleaned:
        return cleaned
    return f"unknown_case_{index:04d}"


def ensure_unique_case_dir(base_dir: Path) -> Path:
    if not base_dir.exists():
        return base_dir
    suffix = 2
    while True:
        candidate = base_dir.parent / f"{base_dir.name}__dup{suffix}"
        if not candidate.exists():
            return candidate
        suffix += 1


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as infile:
        for line_no, line in enumerate(infile, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at line {line_no} in {path}: {exc}") from exc
            if not isinstance(obj, dict):
                raise ValueError(f"JSON line {line_no} is not an object in {path}")
            records.append(obj)
    return records


def build_layout(records: list[dict[str, Any]]) -> BuildStats:
    if OUTPUT_ROOT.exists():
        shutil.rmtree(OUTPUT_ROOT)
    CASES_ROOT.mkdir(parents=True, exist_ok=True)

    stats = BuildStats(total_records_read=len(records))

    with MANIFEST_PATH.open("w", encoding="utf-8") as manifest_file:
        for index, record in enumerate(records, start=1):
            language = normalize_text(record.get("language")) or "unknown"
            authoritative_case_number = choose_authoritative(
                record,
                detail_key="detail_case_number",
                source_key="source_list_case_number",
            )
            authoritative_decision_date = choose_authoritative(
                record,
                detail_key="detail_decision_date",
                source_key="source_list_decision_date",
            )
            case_slug = slugify_case_number(authoritative_case_number, index=index)
            year = extract_year(authoritative_decision_date)

            case_dir = ensure_unique_case_dir(CASES_ROOT / language / year / case_slug)
            case_dir.mkdir(parents=True, exist_ok=True)

            metadata_path = case_dir / "metadata.json"
            full_text_path = case_dir / "full_text.txt"

            full_text = normalize_text(record.get("full_text"))
            full_text_path.write_text(full_text, encoding="utf-8")

            relative_full_text_path = full_text_path.relative_to(OUTPUT_ROOT).as_posix()
            relative_metadata_path = metadata_path.relative_to(OUTPUT_ROOT).as_posix()

            metadata = {
                "court": normalize_text(record.get("court")),
                "source_list_case_number": normalize_text(record.get("source_list_case_number")),
                "source_list_decision_date": normalize_text(record.get("source_list_decision_date")),
                "source_list_case_type": normalize_text(record.get("source_list_case_type")),
                "detail_case_number": normalize_text(record.get("detail_case_number")),
                "detail_decision_date": normalize_text(record.get("detail_decision_date")),
                "detail_title_or_issue": normalize_text(record.get("detail_title_or_issue")),
                "language": language,
                "pdf_url": normalize_text(record.get("pdf_url")),
                "text_url_or_action": normalize_text(record.get("text_url_or_action")),
                "page_number": record.get("page_number"),
                "extraction_source": EXTRACTION_SOURCE,
                "full_text_path": relative_full_text_path,
            }
            metadata_path.write_text(
                json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )

            manifest_record = {
                "language": language,
                "authoritative_case_number": authoritative_case_number,
                "authoritative_decision_date": authoritative_decision_date,
                "court": metadata["court"],
                "pdf_url": metadata["pdf_url"],
                "text_url_or_action": metadata["text_url_or_action"],
                "metadata_path": relative_metadata_path,
                "full_text_path": relative_full_text_path,
            }
            manifest_file.write(json.dumps(manifest_record, ensure_ascii=False) + "\n")

            stats.total_corpus_records_written += 1
            if language == "zh":
                stats.zh_records_written += 1
            if language == "pt":
                stats.pt_records_written += 1
            if authoritative_case_number:
                stats.records_with_authoritative_case_number += 1
            if authoritative_decision_date:
                stats.records_with_authoritative_decision_date += 1

    return stats


def write_report(stats: BuildStats) -> None:
    appears_successful = (
        stats.total_records_read > 0
        and stats.total_records_read == stats.total_corpus_records_written
    )
    lines = [
        "Day 19 raw corpus build report",
        "================================",
        f"total records read: {stats.total_records_read}",
        f"total corpus records written: {stats.total_corpus_records_written}",
        f"zh records written: {stats.zh_records_written}",
        f"pt records written: {stats.pt_records_written}",
        f"records with authoritative case number: {stats.records_with_authoritative_case_number}",
        f"records with authoritative decision date: {stats.records_with_authoritative_decision_date}",
        f"raw corpus layout build appears successful: {'yes' if appears_successful else 'no'}",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_summary(stats: BuildStats) -> None:
    appears_successful = (
        stats.total_records_read > 0
        and stats.total_records_read == stats.total_corpus_records_written
    )
    print(f"total records read: {stats.total_records_read}")
    print(f"total corpus records written: {stats.total_corpus_records_written}")
    print(f"zh records written: {stats.zh_records_written}")
    print(f"pt records written: {stats.pt_records_written}")
    print(
        "records with authoritative case number: "
        f"{stats.records_with_authoritative_case_number}"
    )
    print(
        "records with authoritative decision date: "
        f"{stats.records_with_authoritative_decision_date}"
    )
    print(
        "whether raw corpus layout build appears successful: "
        f"{'yes' if appears_successful else 'no'}"
    )


def main() -> int:
    try:
        if not INPUT_PATH.exists():
            raise FileNotFoundError(f"Input JSONL not found: {INPUT_PATH}")
        records = load_jsonl(INPUT_PATH)
        stats = build_layout(records)
        write_report(stats)
        print_summary(stats)
        return 0
    except Exception as exc:  # basic error handling for CLI usage
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
