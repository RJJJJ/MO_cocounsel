#!/usr/bin/env python3
"""Build Day 63B dense-ready chunk corpus from the latest full-case source.

This script intentionally keeps retrieval unit at chunk-level while refreshing
chunk inputs from `data/corpus/raw/macau_court_cases_full/manifest.jsonl`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from crawler.prep.build_chunking_prep_layer import make_chunk_id, normalize_whitespace, split_into_chunks
from crawler.retrieval.local_bm25_query_prototype import read_jsonl

FULL_CORPUS_ROOT = Path("data/corpus/raw/macau_court_cases_full")
FULL_MANIFEST_PATH = FULL_CORPUS_ROOT / "manifest.jsonl"
DAY63B_DENSE_BASELINE_ROOT = Path("data/corpus/prepared/macau_court_cases/dense_baseline")
DAY63B_DENSE_READY_CHUNKS_PATH = DAY63B_DENSE_BASELINE_ROOT / "day63b_dense_ready_chunks.jsonl"
DAY63B_DENSE_READY_REPORT_PATH = DAY63B_DENSE_BASELINE_ROOT / "day63b_dense_ready_chunks_report.txt"
PREPARED_CHUNKS_PATH = Path("data/corpus/prepared/macau_court_cases/chunks.jsonl")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_manifest(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file_obj:
        for line in file_obj:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _resolve_source_path(source_root: Path, rel_path: str, manifest_row: dict[str, Any], provenance_key: str) -> Path:
    primary = source_root / rel_path
    if primary.exists():
        return primary

    provenance = manifest_row.get("provenance")
    if isinstance(provenance, dict):
        provenance_path = provenance.get(provenance_key, "")
        if provenance_path:
            candidate = Path(str(provenance_path))
            if candidate.exists():
                return candidate
    return primary


def build_day63b_dense_ready_chunks(
    *,
    source_root: Path = FULL_CORPUS_ROOT,
    manifest_path: Path = FULL_MANIFEST_PATH,
    output_path: Path = DAY63B_DENSE_READY_CHUNKS_PATH,
    report_path: Path = DAY63B_DENSE_READY_REPORT_PATH,
) -> dict[str, Any]:
    if not manifest_path.exists():
        raise FileNotFoundError(f"Full corpus manifest not found: {manifest_path}")

    manifest_rows = _read_manifest(manifest_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    total_cases = 0
    total_chunks = 0
    zh_chunks = 0
    pt_chunks = 0
    skipped_cases: list[str] = []

    missing_source_paths = 0

    with output_path.open("w", encoding="utf-8") as out:
        for manifest_row in manifest_rows:
            total_cases += 1

            metadata_rel_path = str(manifest_row.get("metadata_path", "")).strip()
            full_text_rel_path = str(manifest_row.get("full_text_path", "")).strip()
            if not metadata_rel_path or not full_text_rel_path:
                skipped_cases.append(f"missing_paths_manifest_line_{total_cases}")
                continue

            metadata_path = _resolve_source_path(source_root, metadata_rel_path, manifest_row, "source_metadata_path")
            full_text_path = _resolve_source_path(source_root, full_text_rel_path, manifest_row, "source_full_text_path")
            if not metadata_path.exists() or not full_text_path.exists():
                missing_source_paths += 1
                skipped_cases.append(metadata_rel_path)
                continue

            metadata = _read_json(metadata_path)
            full_text = full_text_path.read_text(encoding="utf-8", errors="replace")
            cleaned_text = normalize_whitespace(full_text)
            if not cleaned_text:
                skipped_cases.append(metadata_rel_path)
                continue

            authoritative_case_number = str(manifest_row.get("authoritative_case_number", ""))
            authoritative_decision_date = str(manifest_row.get("authoritative_decision_date", ""))
            court = str(manifest_row.get("court") or metadata.get("court", ""))
            language = str(manifest_row.get("language") or metadata.get("language", ""))
            case_type = str(metadata.get("source_list_case_type", ""))
            pdf_url = str(manifest_row.get("pdf_url") or metadata.get("pdf_url", ""))
            text_url_or_action = str(manifest_row.get("text_url_or_action") or metadata.get("text_url_or_action", ""))

            chunks = split_into_chunks(cleaned_text)
            for idx, chunk_text in enumerate(chunks):
                chunk_record = {
                    "chunk_id": make_chunk_id(
                        authoritative_case_number=authoritative_case_number,
                        authoritative_decision_date=authoritative_decision_date,
                        language=language,
                        chunk_index=idx,
                        chunk_text=chunk_text,
                    ),
                    "authoritative_case_number": authoritative_case_number,
                    "authoritative_decision_date": authoritative_decision_date,
                    "court": court,
                    "language": language,
                    "case_type": case_type,
                    "chunk_index": idx,
                    "chunk_text": chunk_text,
                    "searchable_text": chunk_text,
                    "source_metadata_path": metadata_rel_path,
                    "source_full_text_path": full_text_rel_path,
                    "pdf_url": pdf_url,
                    "text_url_or_action": text_url_or_action,
                }
                out.write(json.dumps(chunk_record, ensure_ascii=False) + "\n")

                total_chunks += 1
                if language == "zh":
                    zh_chunks += 1
                elif language == "pt":
                    pt_chunks += 1

    fallback_used = False
    if total_chunks == 0 and PREPARED_CHUNKS_PATH.exists():
        fallback_used = True
        authoritative_keys = {
            (str(row.get("authoritative_case_number", "")), str(row.get("authoritative_decision_date", "")))
            for row in manifest_rows
        }
        prepared_rows = read_jsonl(PREPARED_CHUNKS_PATH)
        with output_path.open("w", encoding="utf-8") as out:
            for row in prepared_rows:
                key = (
                    str(row.get("authoritative_case_number", "")),
                    str(row.get("authoritative_decision_date", "")),
                )
                if key not in authoritative_keys:
                    continue
                row["searchable_text"] = str(row.get("chunk_text", ""))
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
                total_chunks += 1
                language = str(row.get("language", ""))
                if language == "zh":
                    zh_chunks += 1
                elif language == "pt":
                    pt_chunks += 1

    average_chunks_per_case = (total_chunks / total_cases) if total_cases else 0.0
    success = total_chunks > 0

    report_lines = [
        "Day 63B Dense-ready Chunk Build Report",
        f"source_root: {source_root}",
        f"manifest_path: {manifest_path}",
        f"output_path: {output_path}",
        f"total_cases: {total_cases}",
        f"total_chunks: {total_chunks}",
        f"average_chunks_per_case: {average_chunks_per_case:.2f}",
        f"zh_chunks: {zh_chunks}",
        f"pt_chunks: {pt_chunks}",
        f"skipped_cases_count: {len(skipped_cases)}",
        f"missing_source_paths_count: {missing_source_paths}",
        f"fallback_used_prepared_chunks: {fallback_used}",
        f"success: {success}",
    ]
    if skipped_cases:
        report_lines.append("skipped_cases_examples:")
        report_lines.extend(f"- {case_key}" for case_key in skipped_cases[:20])
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    return {
        "total_cases": total_cases,
        "total_chunks": total_chunks,
        "average_chunks_per_case": average_chunks_per_case,
        "zh_chunks": zh_chunks,
        "pt_chunks": pt_chunks,
        "skipped_cases_count": len(skipped_cases),
        "success": success,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Day 63B dense-ready chunk corpus from full corpus source")
    parser.add_argument("--source-root", type=Path, default=FULL_CORPUS_ROOT)
    parser.add_argument("--manifest", type=Path, default=FULL_MANIFEST_PATH)
    parser.add_argument("--output", type=Path, default=DAY63B_DENSE_READY_CHUNKS_PATH)
    parser.add_argument("--report", type=Path, default=DAY63B_DENSE_READY_REPORT_PATH)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = build_day63b_dense_ready_chunks(
        source_root=args.source_root,
        manifest_path=args.manifest,
        output_path=args.output,
        report_path=args.report,
    )
    print(f"total cases: {summary['total_cases']}")
    print(f"total chunks: {summary['total_chunks']}")
    print(f"average chunks per case: {summary['average_chunks_per_case']:.2f}")
    print(f"zh chunks: {summary['zh_chunks']}")
    print(f"pt chunks: {summary['pt_chunks']}")
    print(f"skipped_cases_count: {summary['skipped_cases_count']}")
    print(f"success: {summary['success']}")


if __name__ == "__main__":
    main()
