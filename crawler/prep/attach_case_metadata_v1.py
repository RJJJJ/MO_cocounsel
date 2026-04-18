#!/usr/bin/env python3
"""Attach case metadata v1 to authoritative merged records in a new output path."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

DEFAULT_MERGED_ROOT = Path("data/corpus/raw/macau_court_cases_full")
DEFAULT_METADATA_INPUT = Path("data/corpus/metadata/case_metadata_v1.jsonl")
DEFAULT_OUTPUT_ROOT = Path("data/corpus/raw/macau_court_cases_full_metadata_v1")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Attach metadata v1 to merged authoritative manifest")
    parser.add_argument("--merged-root", type=Path, default=DEFAULT_MERGED_ROOT)
    parser.add_argument("--manifest-path", type=Path, default=None)
    parser.add_argument("--metadata-input", type=Path, default=DEFAULT_METADATA_INPUT)
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    return parser.parse_args()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            raw = line.strip()
            if not raw:
                continue
            payload = json.loads(raw)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def main() -> None:
    args = parse_args()
    manifest_path = args.manifest_path or (args.merged_root / "manifest.jsonl")

    metadata_rows = load_jsonl(args.metadata_input)
    metadata_by_sentence_id = {
        str(row.get("sentence_id", "")).strip(): row
        for row in metadata_rows
        if str(row.get("sentence_id", "")).strip()
    }

    args.output_root.mkdir(parents=True, exist_ok=True)
    output_manifest = args.output_root / "manifest.metadata_attached_v1.jsonl"
    metadata_copy = args.output_root / "case_metadata_v1.jsonl"
    report_path = args.output_root / "attach_case_metadata_v1_report.json"

    total = 0
    attached = 0
    missing = 0

    with manifest_path.open("r", encoding="utf-8") as src, output_manifest.open("w", encoding="utf-8") as dst:
        for line in src:
            raw = line.strip()
            if not raw:
                continue
            row = json.loads(raw)
            total += 1
            sentence_id = str(row.get("sentence_id", "")).strip()
            metadata_row = metadata_by_sentence_id.get(sentence_id)
            if metadata_row:
                row["case_metadata_v1"] = metadata_row.get("case_metadata_v1", {})
                row["case_metadata_v1_field_sources"] = metadata_row.get("field_sources", {})
                row["case_metadata_v1_schema"] = metadata_row.get("metadata_schema_version", "v1")
                row["case_metadata_v1_attached"] = True
                attached += 1
            else:
                row["case_metadata_v1"] = {
                    "case_summary": "",
                    "holding": "",
                    "disputed_issues": [],
                    "legal_basis": [],
                    "reasoning_summary": "",
                    "doctrinal_point": "",
                }
                row["case_metadata_v1_field_sources"] = {
                    "case_summary": "empty",
                    "holding": "empty",
                    "disputed_issues": "empty",
                    "legal_basis": "empty",
                    "reasoning_summary": "empty",
                    "doctrinal_point": "empty",
                }
                row["case_metadata_v1_schema"] = "v1"
                row["case_metadata_v1_attached"] = False
                missing += 1
            dst.write(json.dumps(row, ensure_ascii=False) + "\n")

    with metadata_copy.open("w", encoding="utf-8") as fh:
        for row in metadata_rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    report = {
        "authoritative_identity": "sentence_id",
        "input_manifest_path": manifest_path.as_posix(),
        "metadata_input": args.metadata_input.as_posix(),
        "output_root": args.output_root.as_posix(),
        "output_manifest": output_manifest.as_posix(),
        "metadata_snapshot": metadata_copy.as_posix(),
        "total_manifest_rows": total,
        "attached_rows": attached,
        "missing_rows": missing,
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
