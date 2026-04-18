#!/usr/bin/env python3
"""Build case-level metadata v1 on top of merged authoritative corpus (sentence_id-first).

Day 64 scope:
- keep retrieval path unchanged
- attach metadata after merge
- fixed 6-field schema for case-level outputs
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_MERGED_ROOT = Path("data/corpus/raw/macau_court_cases_full")
DEFAULT_MODEL_METADATA_PATH = Path("data/eval/model_generated_metadata_output.jsonl")
DEFAULT_BASELINE_METADATA_PATH = Path("data/eval/deterministic_metadata_extraction_baseline_output.jsonl")
DEFAULT_OUTPUT_PATH = Path("data/corpus/metadata/case_metadata_v1.jsonl")
DEFAULT_REPORT_PATH = Path("data/corpus/metadata/case_metadata_v1_report.json")

FIXED_FIELDS = (
    "case_summary",
    "holding",
    "disputed_issues",
    "legal_basis",
    "reasoning_summary",
    "doctrinal_point",
)


@dataclass(frozen=True)
class MergeCaseRow:
    sentence_id: str
    authoritative_case_number: str
    authoritative_decision_date: str
    language: str
    court: str
    case_type: str
    full_text: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build case metadata schema v1 from authoritative merged corpus")
    parser.add_argument("--merged-root", type=Path, default=DEFAULT_MERGED_ROOT)
    parser.add_argument("--manifest-path", type=Path, default=None)
    parser.add_argument("--model-metadata", type=Path, default=DEFAULT_MODEL_METADATA_PATH)
    parser.add_argument("--baseline-metadata", type=Path, default=DEFAULT_BASELINE_METADATA_PATH)
    parser.add_argument("--output-path", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--report-path", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--limit", type=int, default=0, help="optional max rows")
    return parser.parse_args()


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "").replace("\u3000", " ")).strip()


def split_sentences(text: str) -> list[str]:
    if not text:
        return []
    parts = re.split(r"(?<=[。！？!?；;\.])\s+", text)
    return [normalize_space(item) for item in parts if normalize_space(item)]


def clip(text: str, max_chars: int) -> str:
    cleaned = normalize_space(text)
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3] + "..."


def unique_keep_order(items: list[str], limit: int) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for raw in items:
        item = normalize_space(raw)
        key = item.lower()
        if not item or key in seen:
            continue
        seen.add(key)
        result.append(item)
        if len(result) >= limit:
            break
    return result


def normalize_list_field(value: Any, limit: int = 10) -> list[str]:
    if isinstance(value, list):
        candidates = [normalize_space(item) for item in value]
    elif isinstance(value, str):
        candidates = [normalize_space(p) for p in re.split(r"[\n,，、;；]+", value)]
    else:
        candidates = []
    return unique_keep_order(candidates, limit=limit)


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
    return normalize_space(match.group(1)) if match else ""


def deterministic_case_summary(row: MergeCaseRow) -> str:
    if not row.full_text:
        return ""
    block = extract_heading_block(
        row.full_text,
        heading_patterns=[r"案情摘要", r"摘要", r"事實", r"relat[óo]rio", r"resumo", r"sum[áa]rio"],
        stop_patterns=[r"理由", r"法律依據", r"裁判", r"決定", r"fundamenta", r"decis[ãa]o"],
    )
    if block:
        return clip(block, 320)
    sentences = split_sentences(row.full_text)
    return clip(" ".join(sentences[:2]), 320)


def deterministic_holding(row: MergeCaseRow) -> str:
    if not row.full_text:
        return ""
    sentences = split_sentences(row.full_text)
    keywords = [
        "裁定",
        "判決",
        "判處",
        "駁回",
        "上訴",
        "維持原判",
        "改判",
        "acordam",
        "decidem",
        "decisão",
        "julgar",
        "negar provimento",
        "conceder provimento",
        "condenar",
        "absolver",
    ]
    hits = [s for s in sentences if any(k.lower() in s.lower() for k in keywords)]
    if hits:
        # keep short answer style: max 3 sentences
        return clip(" ".join(hits[-3:]), 260)
    return clip(" ".join(sentences[-2:]), 260)


def deterministic_disputed_issues(row: MergeCaseRow) -> list[str]:
    if not row.full_text:
        return unique_keep_order([row.case_type], limit=6)
    patterns = [
        r"爭議焦點\s*[:：]\s*([^。\n]+)",
        r"主要問題\s*[:：]\s*([^。\n]+)",
        r"quest[õo]es?\s*[:：]\s*([^\.\n]+)",
        r"objecto\s*[:：]\s*([^\.\n]+)",
    ]
    candidates: list[str] = []
    for pattern in patterns:
        match = re.search(pattern, row.full_text, flags=re.IGNORECASE)
        if not match:
            continue
        candidates.extend(re.split(r"[、，,;；]+", match.group(1)))
    if row.case_type:
        candidates.append(row.case_type)
    return unique_keep_order(candidates, limit=8)


def deterministic_legal_basis(row: MergeCaseRow) -> list[str]:
    if not row.full_text:
        return []
    zh = [re.sub(r"\s+", "", m) for m in re.findall(r"第\s*\d+\s*(?:之\s*\d+)?\s*條", row.full_text)]
    pt = [normalize_space(m) for m in re.findall(r"art(?:igo|\.)?\s*\d+[.º°o]*", row.full_text, flags=re.IGNORECASE)]
    return unique_keep_order(zh + pt, limit=12)


def deterministic_reasoning_summary(row: MergeCaseRow) -> str:
    if not row.full_text:
        return ""
    block = extract_heading_block(
        row.full_text,
        heading_patterns=[r"理由", r"理由說明", r"法律分析", r"fundamenta[cç][ãa]o", r"fundamentos"],
        stop_patterns=[r"裁判", r"決定", r"結論", r"decis[ãa]o"],
    )
    if block:
        return clip(block, 360)
    sentences = split_sentences(row.full_text)
    picked = [s for s in sentences if any(k in s for k in ["理由", "認為", "因此", "fundament", "entende"])]
    return clip(" ".join(picked[:3] if picked else sentences[:3]), 360)


def deterministic_doctrinal_point(row: MergeCaseRow) -> str:
    if not row.full_text:
        return ""
    patterns = [
        r"裁判要旨\s*[:：]\s*([^。\n]+)",
        r"法律見解\s*[:：]\s*([^。\n]+)",
        r"法理\s*[:：]\s*([^。\n]+)",
        r"sum[áa]rio\s*[:：]\s*([^\.\n]+)",
    ]
    for pattern in patterns:
        match = re.search(pattern, row.full_text, flags=re.IGNORECASE)
        if match:
            return clip(match.group(1), 220)
    sentences = split_sentences(row.full_text)
    picked = [s for s in sentences if any(k in s for k in ["本院認為", "本案", "原則", "應", "deve", "princípio"])]
    return clip((picked[0] if picked else ""), 220)


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


def load_existing_metadata_index(path: Path) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    by_case_number: dict[str, dict[str, Any]] = {}
    by_sentence_id: dict[str, dict[str, Any]] = {}
    for payload in load_jsonl(path):
        core = payload.get("core_case_metadata") or {}
        generated = payload.get("generated_digest_metadata") or payload.get("case_metadata_v1") or {}
        normalized = {
            "case_summary": normalize_space(generated.get("case_summary")),
            "holding": normalize_space(generated.get("holding")),
            "disputed_issues": normalize_list_field(generated.get("disputed_issues"), limit=10),
            "legal_basis": normalize_list_field(generated.get("legal_basis"), limit=12),
            "reasoning_summary": normalize_space(generated.get("reasoning_summary")),
            "doctrinal_point": normalize_space(generated.get("doctrinal_point")),
        }

        sentence_id = normalize_space(payload.get("sentence_id") or core.get("sentence_id"))
        if sentence_id:
            by_sentence_id[sentence_id] = normalized

        case_number = normalize_space(
            core.get("authoritative_case_number")
            or payload.get("authoritative_case_number")
            or payload.get("case_number")
        )
        if case_number:
            by_case_number[case_number] = normalized
    return by_case_number, by_sentence_id


def read_merged_cases(merged_root: Path, manifest_path: Path, limit: int) -> list[MergeCaseRow]:
    rows: list[MergeCaseRow] = []
    with manifest_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            raw = line.strip()
            if not raw:
                continue
            payload = json.loads(raw)
            sentence_id = normalize_space(payload.get("sentence_id"))
            if not sentence_id:
                continue

            metadata_rel = normalize_space(payload.get("metadata_path"))
            full_text_rel = normalize_space(payload.get("full_text_path"))
            full_text = ""
            case_type = ""

            if metadata_rel:
                metadata_path = merged_root / metadata_rel
                if metadata_path.exists():
                    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                    case_type = normalize_space(metadata.get("source_list_case_type"))

            if full_text_rel:
                full_text_path = merged_root / full_text_rel
                if full_text_path.exists():
                    full_text = normalize_space(full_text_path.read_text(encoding="utf-8"))

            rows.append(
                MergeCaseRow(
                    sentence_id=sentence_id,
                    authoritative_case_number=normalize_space(payload.get("authoritative_case_number")),
                    authoritative_decision_date=normalize_space(payload.get("authoritative_decision_date")),
                    language=normalize_space(payload.get("language")),
                    court=normalize_space(payload.get("court")),
                    case_type=case_type,
                    full_text=full_text,
                )
            )
            if limit > 0 and len(rows) >= limit:
                break
    return rows


def pick_field(
    *,
    field: str,
    model_row: dict[str, Any],
    baseline_row: dict[str, Any],
    deterministic_value: Any,
) -> tuple[Any, str]:
    if field in ("disputed_issues", "legal_basis"):
        model_val = normalize_list_field(model_row.get(field), limit=12)
        if model_val:
            return model_val, "model_generated"
        baseline_val = normalize_list_field(baseline_row.get(field), limit=12)
        if baseline_val:
            return baseline_val, "deterministic_fallback"
        deterministic_list = normalize_list_field(deterministic_value, limit=12)
        if deterministic_list:
            return deterministic_list, "deterministic_fallback"
        return [], "empty"

    model_text = normalize_space(model_row.get(field))
    if model_text:
        return model_text, "model_generated"
    baseline_text = normalize_space(baseline_row.get(field))
    if baseline_text:
        return baseline_text, "deterministic_fallback"
    det_text = normalize_space(deterministic_value)
    if det_text:
        return det_text, "deterministic_fallback"
    return "", "empty"


def build_case_metadata_v1(
    *,
    cases: list[MergeCaseRow],
    model_index: dict[str, dict[str, Any]],
    model_sentence_index: dict[str, dict[str, Any]],
    baseline_index: dict[str, dict[str, Any]],
    baseline_sentence_index: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    field_non_empty = {name: 0 for name in FIXED_FIELDS}
    full_6_non_empty = 0

    for case in cases:
        model_row = model_sentence_index.get(case.sentence_id) or model_index.get(case.authoritative_case_number, {})
        baseline_row = baseline_sentence_index.get(case.sentence_id) or baseline_index.get(case.authoritative_case_number, {})

        deterministic_values = {
            "case_summary": deterministic_case_summary(case),
            "holding": deterministic_holding(case),
            "disputed_issues": deterministic_disputed_issues(case),
            "legal_basis": deterministic_legal_basis(case),
            "reasoning_summary": deterministic_reasoning_summary(case),
            "doctrinal_point": deterministic_doctrinal_point(case),
        }

        metadata: dict[str, Any] = {}
        sources: dict[str, str] = {}
        for field in FIXED_FIELDS:
            value, source = pick_field(
                field=field,
                model_row=model_row,
                baseline_row=baseline_row,
                deterministic_value=deterministic_values[field],
            )
            metadata[field] = value
            sources[field] = source
            if isinstance(value, list) and value:
                field_non_empty[field] += 1
            if isinstance(value, str) and normalize_space(value):
                field_non_empty[field] += 1

        if all((metadata[name] if isinstance(metadata[name], list) else normalize_space(metadata[name])) for name in FIXED_FIELDS):
            full_6_non_empty += 1

        rows.append(
            {
                "sentence_id": case.sentence_id,
                "authoritative_case_number": case.authoritative_case_number,
                "authoritative_decision_date": case.authoritative_decision_date,
                "language": case.language,
                "court": case.court,
                "case_metadata_v1": metadata,
                "field_sources": sources,
                "metadata_schema_version": "v1",
            }
        )

    total = len(rows)
    non_empty_ratio = {
        field: (field_non_empty[field] / total if total else 0.0) for field in FIXED_FIELDS
    }
    summary = {
        "total_cases": total,
        "full_6_fields_non_empty": full_6_non_empty,
        "field_non_empty_count": field_non_empty,
        "field_non_empty_ratio": non_empty_ratio,
    }
    return rows, summary


def main() -> None:
    args = parse_args()
    merged_root = args.merged_root
    manifest_path = args.manifest_path or (merged_root / "manifest.jsonl")

    cases = read_merged_cases(merged_root=merged_root, manifest_path=manifest_path, limit=max(args.limit, 0))
    model_index, model_sentence_index = load_existing_metadata_index(args.model_metadata)
    baseline_index, baseline_sentence_index = load_existing_metadata_index(args.baseline_metadata)

    rows, summary = build_case_metadata_v1(
        cases=cases,
        model_index=model_index,
        model_sentence_index=model_sentence_index,
        baseline_index=baseline_index,
        baseline_sentence_index=baseline_sentence_index,
    )

    args.output_path.parent.mkdir(parents=True, exist_ok=True)
    with args.output_path.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")

    report = {
        "metadata_schema_version": "v1",
        "authoritative_identity": "sentence_id",
        "input_manifest_path": manifest_path.as_posix(),
        "model_metadata_path": args.model_metadata.as_posix(),
        "baseline_metadata_path": args.baseline_metadata.as_posix(),
        "output_path": args.output_path.as_posix(),
        "summary": summary,
    }
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
