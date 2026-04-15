#!/usr/bin/env python3
"""Build chunking-ready records from Macau court raw corpus."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

RAW_CORPUS_ROOT = Path("data/corpus/raw/macau_court_cases")
MANIFEST_PATH = RAW_CORPUS_ROOT / "manifest.jsonl"
PREPARED_ROOT = Path("data/corpus/prepared/macau_court_cases")
CHUNKS_PATH = PREPARED_ROOT / "chunks.jsonl"
REPORT_PATH = PREPARED_ROOT / "chunking_prep_report.txt"

TARGET_CHUNK_SIZE = 1200
MAX_CHUNK_SIZE = 1600


def normalize_whitespace(text: str) -> str:
    """Normalize whitespace while preserving legal text semantics."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    normalized_lines = []
    for line in text.split("\n"):
        cleaned_line = re.sub(r"[ \t]+", " ", line).strip()
        normalized_lines.append(cleaned_line)
    normalized = "\n".join(normalized_lines)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def split_chunk_fixed(text: str, chunk_size: int = TARGET_CHUNK_SIZE) -> list[str]:
    """Fallback fixed-size splitting for very long single-paragraph text."""
    if not text:
        return []
    return [text[i : i + chunk_size].strip() for i in range(0, len(text), chunk_size) if text[i : i + chunk_size].strip()]


def split_into_chunks(text: str) -> list[str]:
    """Paragraph-aware splitting with fixed-size fallback."""
    if not text:
        return []

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return split_chunk_fixed(text)

    chunks: list[str] = []
    buffer = ""

    for paragraph in paragraphs:
        if len(paragraph) > MAX_CHUNK_SIZE:
            if buffer:
                chunks.append(buffer)
                buffer = ""
            chunks.extend(split_chunk_fixed(paragraph))
            continue

        candidate = f"{buffer}\n\n{paragraph}" if buffer else paragraph
        if len(candidate) <= TARGET_CHUNK_SIZE:
            buffer = candidate
        else:
            if buffer:
                chunks.append(buffer)
            buffer = paragraph

    if buffer:
        chunks.append(buffer)

    return chunks


def make_chunk_id(
    authoritative_case_number: str,
    authoritative_decision_date: str,
    language: str,
    chunk_index: int,
    chunk_text: str,
) -> str:
    payload = "|".join(
        [
            authoritative_case_number,
            authoritative_decision_date,
            language,
            str(chunk_index),
            chunk_text,
        ]
    )
    digest = hashlib.sha1(payload.encode("utf-8")).hexdigest()[:12]
    return f"{authoritative_case_number.replace('/', '_')}_{language}_c{chunk_index:04d}_{digest}"


def read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as file_obj:
        return json.load(file_obj)


def read_manifest(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file_obj:
        for line in file_obj:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def build_chunking_prep() -> dict[str, Any]:
    if not MANIFEST_PATH.exists():
        raise FileNotFoundError(f"Manifest not found: {MANIFEST_PATH}")

    manifest_records = read_manifest(MANIFEST_PATH)
    PREPARED_ROOT.mkdir(parents=True, exist_ok=True)

    total_cases = 0
    total_chunks = 0
    zh_chunks = 0
    pt_chunks = 0
    skipped_cases: list[str] = []

    with CHUNKS_PATH.open("w", encoding="utf-8") as output_file:
        for manifest_record in manifest_records:
            total_cases += 1
            try:
                metadata_rel_path = manifest_record["metadata_path"]
                full_text_rel_path = manifest_record["full_text_path"]
            except KeyError:
                skipped_cases.append(f"missing_paths_in_manifest_record_{total_cases}")
                continue

            metadata_path = RAW_CORPUS_ROOT / metadata_rel_path
            full_text_path = RAW_CORPUS_ROOT / full_text_rel_path

            if not metadata_path.exists() or not full_text_path.exists():
                skipped_cases.append(str(metadata_rel_path))
                continue

            metadata = read_json(metadata_path)
            full_text = full_text_path.read_text(encoding="utf-8", errors="replace")
            cleaned_text = normalize_whitespace(full_text)

            if not cleaned_text:
                skipped_cases.append(str(metadata_rel_path))
                continue

            authoritative_case_number = manifest_record.get("authoritative_case_number", "")
            authoritative_decision_date = manifest_record.get("authoritative_decision_date", "")
            court = manifest_record.get("court") or metadata.get("court", "")
            language = manifest_record.get("language") or metadata.get("language", "")
            case_type = metadata.get("source_list_case_type", "")
            pdf_url = manifest_record.get("pdf_url") or metadata.get("pdf_url", "")
            text_url_or_action = manifest_record.get("text_url_or_action") or metadata.get("text_url_or_action", "")

            chunks = split_into_chunks(cleaned_text)
            for idx, chunk_text in enumerate(chunks):
                chunk_record = {
                    "authoritative_case_number": authoritative_case_number,
                    "authoritative_decision_date": authoritative_decision_date,
                    "court": court,
                    "language": language,
                    "case_type": case_type,
                    "chunk_id": make_chunk_id(
                        authoritative_case_number=authoritative_case_number,
                        authoritative_decision_date=authoritative_decision_date,
                        language=language,
                        chunk_index=idx,
                        chunk_text=chunk_text,
                    ),
                    "chunk_index": idx,
                    "chunk_text": chunk_text,
                    "source_metadata_path": metadata_rel_path,
                    "source_full_text_path": full_text_rel_path,
                    "pdf_url": pdf_url,
                    "text_url_or_action": text_url_or_action,
                }
                output_file.write(json.dumps(chunk_record, ensure_ascii=False) + "\n")

                total_chunks += 1
                if language == "zh":
                    zh_chunks += 1
                elif language == "pt":
                    pt_chunks += 1

    average_chunks_per_case = (total_chunks / total_cases) if total_cases else 0.0
    success = total_chunks > 0 and len(skipped_cases) < total_cases

    report_lines = [
        "Chunking Prep Report - Macau Court Cases",
        f"manifest_path: {MANIFEST_PATH}",
        f"chunks_output_path: {CHUNKS_PATH}",
        f"total_corpus_records_read: {total_cases}",
        f"total_chunk_records_written: {total_chunks}",
        f"average_chunks_per_case: {average_chunks_per_case:.2f}",
        f"zh_chunks_count: {zh_chunks}",
        f"pt_chunks_count: {pt_chunks}",
        f"skipped_cases_count: {len(skipped_cases)}",
        f"chunking_prep_successful: {success}",
    ]

    if skipped_cases:
        report_lines.append("skipped_cases_examples:")
        report_lines.extend(f"- {case_path}" for case_path in skipped_cases[:20])

    REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    return {
        "total_cases": total_cases,
        "total_chunks": total_chunks,
        "average_chunks_per_case": average_chunks_per_case,
        "zh_chunks": zh_chunks,
        "pt_chunks": pt_chunks,
        "success": success,
    }


def main() -> None:
    try:
        summary = build_chunking_prep()
        print(f"total corpus records read: {summary['total_cases']}")
        print(f"total chunk records written: {summary['total_chunks']}")
        print(f"average chunks per case: {summary['average_chunks_per_case']:.2f}")
        print(f"zh chunks count: {summary['zh_chunks']}")
        print(f"pt chunks count: {summary['pt_chunks']}")
        print(f"chunking prep appears successful: {summary['success']}")
    except Exception as exc:  # basic top-level error handling
        print(f"chunking prep failed: {exc}")
        raise


if __name__ == "__main__":
    main()
