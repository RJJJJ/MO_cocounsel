#!/usr/bin/env python3
"""Build BM25-ready records from prepared Macau court chunk corpus."""

from __future__ import annotations

import json
import re
import unicodedata
from pathlib import Path
from typing import Any

PREPARED_ROOT = Path("data/corpus/prepared/macau_court_cases")
CHUNKS_PATH = PREPARED_ROOT / "chunks.jsonl"
BM25_CHUNKS_PATH = PREPARED_ROOT / "bm25_chunks.jsonl"
BM25_REPORT_PATH = PREPARED_ROOT / "bm25_prep_report.txt"


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file_obj:
        for line in file_obj:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def normalize_for_bm25(text: str) -> str:
    """Normalize text into a lexical-search-friendly representation."""
    if not text:
        return ""

    normalized = unicodedata.normalize("NFKC", text)
    normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
    normalized = normalized.lower()

    # Preserve CJK and Latin/digit word signals, strip punctuation noise.
    normalized = re.sub(r"[^\w\s\u4e00-\u9fff]", " ", normalized)
    normalized = re.sub(r"_", " ", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()

    return normalized


def build_bm25_record(chunk_record: dict[str, Any]) -> dict[str, Any]:
    chunk_text = chunk_record.get("chunk_text", "")
    bm25_text = normalize_for_bm25(chunk_text)

    return {
        "chunk_id": chunk_record.get("chunk_id", ""),
        "authoritative_case_number": chunk_record.get("authoritative_case_number", ""),
        "authoritative_decision_date": chunk_record.get("authoritative_decision_date", ""),
        "court": chunk_record.get("court", ""),
        "language": chunk_record.get("language", ""),
        "case_type": chunk_record.get("case_type", ""),
        "chunk_text": chunk_text,
        "bm25_text": bm25_text,
        "source_metadata_path": chunk_record.get("source_metadata_path", ""),
        "source_full_text_path": chunk_record.get("source_full_text_path", ""),
        "pdf_url": chunk_record.get("pdf_url", ""),
        "text_url_or_action": chunk_record.get("text_url_or_action", ""),
    }


def build_bm25_prep_layer() -> dict[str, Any]:
    if not CHUNKS_PATH.exists():
        raise FileNotFoundError(f"Chunks file not found: {CHUNKS_PATH}")

    chunk_records = read_jsonl(CHUNKS_PATH)
    PREPARED_ROOT.mkdir(parents=True, exist_ok=True)

    total_chunks = len(chunk_records)
    total_bm25_records = 0
    zh_records = 0
    pt_records = 0
    total_bm25_text_length = 0

    with BM25_CHUNKS_PATH.open("w", encoding="utf-8") as output_file:
        for chunk_record in chunk_records:
            bm25_record = build_bm25_record(chunk_record)
            output_file.write(json.dumps(bm25_record, ensure_ascii=False) + "\n")

            total_bm25_records += 1
            total_bm25_text_length += len(bm25_record["bm25_text"])

            language = bm25_record.get("language", "")
            if language == "zh":
                zh_records += 1
            elif language == "pt":
                pt_records += 1

    average_bm25_text_length = (total_bm25_text_length / total_bm25_records) if total_bm25_records else 0.0
    success = total_chunks > 0 and total_chunks == total_bm25_records

    report_lines = [
        "BM25 Prep Report - Macau Court Cases",
        f"chunks_input_path: {CHUNKS_PATH}",
        f"bm25_output_path: {BM25_CHUNKS_PATH}",
        f"total_chunks_read: {total_chunks}",
        f"total_bm25_records_written: {total_bm25_records}",
        f"zh_records_count: {zh_records}",
        f"pt_records_count: {pt_records}",
        f"average_bm25_text_length: {average_bm25_text_length:.2f}",
        f"bm25_prep_successful: {success}",
    ]
    BM25_REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    return {
        "total_chunks": total_chunks,
        "total_bm25_records": total_bm25_records,
        "zh_records": zh_records,
        "pt_records": pt_records,
        "average_bm25_text_length": average_bm25_text_length,
        "success": success,
    }


def main() -> None:
    try:
        summary = build_bm25_prep_layer()
        print(f"total chunks read: {summary['total_chunks']}")
        print(f"total bm25 records written: {summary['total_bm25_records']}")
        print(f"zh records count: {summary['zh_records']}")
        print(f"pt records count: {summary['pt_records']}")
        print(f"average bm25_text length: {summary['average_bm25_text_length']:.2f}")
        print(f"bm25 prep appears successful: {summary['success']}")
    except Exception as exc:  # basic top-level error handling
        print(f"bm25 prep failed: {exc}")
        raise


if __name__ == "__main__":
    main()
