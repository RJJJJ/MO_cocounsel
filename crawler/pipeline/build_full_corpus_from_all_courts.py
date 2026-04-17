#!/usr/bin/env python3
"""Day 60: build authoritative full corpus by per-court convergence crawl -> merge -> dedupe.

Authoritative flow (Day 60):
1) crawl each court separately (tui/tsi/tjb/ta)
   - Day 60: repeatedly rescan each court from homepage-form snapshot until convergence
     (configured consecutive zero-new-sentence_id rounds), then move to next court.
2) merge all court manifests into one candidate pool
3) dedupe after merge with auditable reasons
4) publish merged authoritative corpus for downstream retrieval/prep
5) attach metadata *after* merged corpus selection (model-preferred, deterministic fallback)

This script intentionally does not use `court=all` as the authoritative source.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from crawler.metadata.metadata_artifact_selection import resolve_model_metadata_path
from crawler.pipeline.add_all_court_crawling_mode import (
    ensure_unique_case_dir,
    extract_sentence_id_from_url,
    extract_year,
    get_sentence_id,
    read_manifest,
    slugify_case_number,
)

COURTS = ("tui", "tsi", "tjb", "ta")
DEFAULT_PER_COURT_ROOT = Path("data/corpus/raw/per_court_runs")
DEFAULT_MERGED_ROOT = Path("data/corpus/raw/macau_court_cases_full")
DEFAULT_CRAWL_SCRIPT = Path("crawler/pipeline/add_all_court_crawling_mode.py")
DEFAULT_MODEL_METADATA_PATH = Path("data/eval/model_generated_metadata_output.jsonl")
DEFAULT_BASELINE_METADATA_PATH = Path("data/eval/deterministic_metadata_extraction_baseline_output.jsonl")


@dataclass(frozen=True)
class CourtRunSummary:
    court: str
    manifest_path: str
    raw_records: int
    candidates_with_sentence_id: int
    missing_sentence_id_skipped: int
    duplicate_sentence_id_skipped: int
    rounds_run: int = 0
    total_unique_sentence_id_discovered: int = 0
    new_corpus_records_added: int = 0
    convergence_stop_reason: str = ""


@dataclass(frozen=True)
class MergeStats:
    per_court_counts: dict[str, dict[str, int]]
    merged_candidate_total: int
    merged_after_dedupe_total: int
    duplicates_total: int
    duplicates_by_reason: dict[str, int]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Day 60 authoritative merged corpus from per-court convergence crawls")
    parser.add_argument("--courts", nargs="+", default=list(COURTS), help="court modes to run")
    parser.add_argument("--start-page", type=int, default=1, help="crawl start page")
    parser.add_argument("--end-page", type=int, default=10, help="crawl end page")
    parser.add_argument("--until-converged", action="store_true", help="enable Day 60 per-court convergence mode")
    parser.add_argument("--max-rounds", type=int, default=6, help="max rounds per court in convergence mode")
    parser.add_argument("--zero-new-round-stop", type=int, default=2, help="consecutive zero-new rounds before stop")
    parser.add_argument("--max-pages-per-round", type=int, default=0, help="page cap per round passed to child")
    parser.add_argument(
        "--max-consecutive-no-new-pages",
        type=int,
        default=0,
        help="optional per-round early stop when consecutive pages discover zero new sentence_id",
    )
    parser.add_argument("--per-court-root", type=Path, default=DEFAULT_PER_COURT_ROOT)
    parser.add_argument("--merged-root", type=Path, default=DEFAULT_MERGED_ROOT)
    parser.add_argument("--crawl-script", type=Path, default=DEFAULT_CRAWL_SCRIPT)
    parser.add_argument(
        "--skip-crawl",
        action="store_true",
        help="skip crawl subprocesses and consume manifests from --court-manifest",
    )
    parser.add_argument(
        "--court-manifest",
        action="append",
        default=[],
        help="explicit input override: format court=path/to/manifest.jsonl (repeatable)",
    )
    parser.add_argument("--model-metadata", type=Path, default=DEFAULT_MODEL_METADATA_PATH)
    parser.add_argument("--baseline-metadata", type=Path, default=DEFAULT_BASELINE_METADATA_PATH)
    parser.add_argument("--json", action="store_true", help="print full JSON summary")
    return parser.parse_args()


def _normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _parse_explicit_manifest_overrides(items: list[str]) -> dict[str, Path]:
    overrides: dict[str, Path] = {}
    for raw in items:
        if "=" not in raw:
            raise ValueError(f"Invalid --court-manifest entry: {raw}; expected court=path")
        court, raw_path = raw.split("=", 1)
        court = court.strip().lower()
        path = Path(raw_path).expanduser()
        overrides[court] = path
    return overrides


def _run_per_court_crawl(args: argparse.Namespace, court: str) -> tuple[Path, dict[str, Any]]:
    # Day 59A hotfix note:
    # Child crawl exit code semantics now distinguish run completion from harvest completeness.
    # exit=0 may be either "success" or "partial_success" (e.g., late-page timeout after useful pages),
    # which is acceptable for parent full-corpus assembly in this round.
    # Parent still fail-fast on non-zero exit codes, which represent true fatal failures.
    court_root = args.per_court_root / court
    report_path = court_root / "all_court_crawl_report.txt"
    child_summary_path = court_root / "child_run_summary.json"
    court_root.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(args.crawl_script),
        "--court",
        court,
        "--start-page",
        str(max(args.start_page, 1)),
        "--end-page",
        str(max(args.end_page, max(args.start_page, 1))),
        "--corpus-root",
        str(court_root),
        "--report-path",
        str(report_path),
        "--child-summary-path",
        str(child_summary_path),
    ]
    if args.until_converged:
        cmd.extend(
            [
                "--until-converged",
                "--max-rounds",
                str(max(1, args.max_rounds)),
                "--zero-new-round-stop",
                str(max(1, args.zero_new_round_stop)),
                "--max-pages-per-round",
                str(max(0, args.max_pages_per_round)),
                "--max-consecutive-no-new-pages",
                str(max(0, args.max_consecutive_no_new_pages)),
            ]
        )
    print(f"[day59] running per-court crawl: {' '.join(cmd)}")
    completed = subprocess.run(cmd, cwd=REPO_ROOT, check=False)
    if completed.returncode != 0:
        raise RuntimeError(f"Per-court crawl failed for {court} with exit code {completed.returncode}")
    print(f"[day59] per-court crawl completed for {court} (exit=0; success or partial_success accepted)")

    manifest_path = court_root / "manifest.jsonl"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found after crawl for court={court}: {manifest_path}")
    summary: dict[str, Any] = {}
    if child_summary_path.exists():
        summary = json.loads(child_summary_path.read_text(encoding="utf-8"))
    return manifest_path, summary


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL row in {path} line {line_no}: {exc}") from exc
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def _build_metadata_index(path: Path) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for payload in _load_jsonl(path):
        core = payload.get("core_case_metadata") or {}
        generated = payload.get("generated_digest_metadata") or {}
        case_number = _normalize_space(
            core.get("authoritative_case_number")
            or payload.get("authoritative_case_number")
            or payload.get("case_number")
        )
        if not case_number:
            continue
        index[case_number] = {
            "case_summary": _normalize_space(generated.get("case_summary") or payload.get("case_summary")),
            "holding": _normalize_space(generated.get("holding") or payload.get("holding")),
            "legal_basis": generated.get("legal_basis") or payload.get("legal_basis") or [],
            "disputed_issues": generated.get("disputed_issues") or payload.get("disputed_issues") or [],
        }
    return index


def _copy_record_to_authoritative_corpus(
    *,
    merged_root: Path,
    manifest_fh,
    record: dict[str, Any],
    full_text: str,
    index: int,
) -> tuple[str, str]:
    cases_root = merged_root / "cases"
    language = _normalize_space(record.get("language")) or "unknown"
    authoritative_case_number = _normalize_space(record.get("authoritative_case_number"))
    authoritative_decision_date = _normalize_space(record.get("authoritative_decision_date"))

    case_slug = slugify_case_number(authoritative_case_number, index=index)
    year = extract_year(authoritative_decision_date)
    case_dir = ensure_unique_case_dir(cases_root / language / year / case_slug)
    case_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = case_dir / "metadata.json"
    full_text_path = case_dir / "full_text.txt"
    full_text_path.write_text(full_text, encoding="utf-8")

    rel_metadata = metadata_path.relative_to(merged_root).as_posix()
    rel_full_text = full_text_path.relative_to(merged_root).as_posix()

# 定義代號與實際法院名稱的映射
    COURT_NAME_MAP = {
        "tui": "終審法院",
        "tsi": "中級法院",
        "tjb": "初級法院",
        "ta": "行政法院"
    }
    
    # 從 record 提取 origin_court_mode (例如 'tui')
    origin_court = record.get("provenance", {}).get("origin_court_mode")
    
    # 如果有對應的名稱就轉換，否則保留原本的 "澳門法院"
    actual_court_name = COURT_NAME_MAP.get(origin_court) or _normalize_space(record.get("court"))

    metadata_payload = {
        "court": actual_court_name,  # 改用映射後的具體法院名稱
        "source_list_case_number": authoritative_case_number,
        "source_list_decision_date": authoritative_decision_date,
        "source_list_case_type": _normalize_space(record.get("source_list_case_type")),
        "language": language,
        "pdf_url": _normalize_space(record.get("pdf_url")),
        "pdf_url_primary": _normalize_space(record.get("pdf_url_primary") or record.get("pdf_url")),
        "pdf_url_zh": _normalize_space(record.get("pdf_url_zh")),
        "pdf_url_pt": _normalize_space(record.get("pdf_url_pt")),
        "text_url_or_action": _normalize_space(record.get("text_url_or_action")),
        "text_url_primary": _normalize_space(record.get("text_url_primary") or record.get("text_url_or_action")),
        "text_url_zh": _normalize_space(record.get("text_url_zh")),
        "text_url_pt": _normalize_space(record.get("text_url_pt")),
        "document_links": record.get("document_links") or [],
        "sentence_id": _normalize_space(record.get("sentence_id")),
        "extraction_source": "day59_per_court_merge_dedupe",
        "provenance": record.get("provenance") or {},
        "full_text_path": rel_full_text,
    }
    metadata_path.write_text(json.dumps(metadata_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest_row = {
        "language": language,
        "authoritative_case_number": authoritative_case_number,
        "authoritative_decision_date": authoritative_decision_date,
        "court": metadata_payload["court"],
        "pdf_url": metadata_payload["pdf_url"],
        "pdf_url_primary": metadata_payload["pdf_url_primary"],
        "pdf_url_zh": metadata_payload["pdf_url_zh"],
        "pdf_url_pt": metadata_payload["pdf_url_pt"],
        "text_url_or_action": metadata_payload["text_url_or_action"],
        "text_url_primary": metadata_payload["text_url_primary"],
        "text_url_zh": metadata_payload["text_url_zh"],
        "text_url_pt": metadata_payload["text_url_pt"],
        "document_links": metadata_payload["document_links"],
        "sentence_id": metadata_payload["sentence_id"],
        "metadata_path": rel_metadata,
        "full_text_path": rel_full_text,
        "provenance": metadata_payload["provenance"],
    }
    manifest_fh.write(json.dumps(manifest_row, ensure_ascii=False) + "\n")
    return rel_metadata, rel_full_text


def _collect_merge_candidates(manifest_path: Path, court: str) -> list[dict[str, Any]]:
    court_root = manifest_path.parent
    candidates: list[dict[str, Any]] = []
    for line_no, row in enumerate(read_manifest(manifest_path), start=1):
        metadata_rel = _normalize_space(row.get("metadata_path"))
        full_text_rel = _normalize_space(row.get("full_text_path"))
        if not metadata_rel or not full_text_rel:
            continue

        metadata_path = court_root / metadata_rel
        full_text_path = court_root / full_text_rel
        if not metadata_path.exists() or not full_text_path.exists():
            continue

        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        full_text = full_text_path.read_text(encoding="utf-8")
        sentence_id = _normalize_space(row.get("sentence_id") or metadata.get("sentence_id"))
        if not sentence_id:
            sentence_id = (
                extract_sentence_id_from_url(row.get("text_url_primary"))
                or extract_sentence_id_from_url(row.get("text_url_zh"))
                or extract_sentence_id_from_url(row.get("text_url_pt"))
                or extract_sentence_id_from_url(row.get("text_url_or_action"))
                or get_sentence_id(row)
            )
        candidate = {
            **row,
            "sentence_id": sentence_id,
            "source_list_case_type": metadata.get("source_list_case_type"),
            "language": _normalize_space(row.get("language") or metadata.get("language")),
            "full_text": full_text,
            "provenance": {
                "origin_court_mode": court,
                "source_manifest_path": manifest_path.as_posix(),
                "source_manifest_line": line_no,
                "source_metadata_path": metadata_path.as_posix(),
                "source_full_text_path": full_text_path.as_posix(),
            },
        }
        candidates.append(candidate)
    return candidates


def _dedupe_and_write_authoritative_corpus(
    *,
    candidates: list[dict[str, Any]],
    merged_root: Path,
) -> MergeStats:
    merged_root.mkdir(parents=True, exist_ok=True)
    (merged_root / "cases").mkdir(parents=True, exist_ok=True)

    per_court_counts: dict[str, dict[str, int]] = {}
    unique_candidates: list[dict[str, Any]] = []
    seen_sentence_ids: set[str] = set()
    duplicate_breakdown = {"duplicate_sentence_id": 0, "missing_sentence_id_skipped": 0}

    for candidate in candidates:
        origin_court = _normalize_space(candidate.get("provenance", {}).get("origin_court_mode")) or "unknown"
        if origin_court not in per_court_counts:
            per_court_counts[origin_court] = {
                "raw_candidates": 0,
                "candidates_with_sentence_id": 0,
                "missing_sentence_id_skipped": 0,
                "duplicate_sentence_id_skipped": 0,
            }
        per_court_counts[origin_court]["raw_candidates"] += 1

        sentence_id = _normalize_space(candidate.get("sentence_id"))
        if not sentence_id:
            per_court_counts[origin_court]["missing_sentence_id_skipped"] += 1
            duplicate_breakdown["missing_sentence_id_skipped"] += 1
            continue
        per_court_counts[origin_court]["candidates_with_sentence_id"] += 1
        if sentence_id in seen_sentence_ids:
            per_court_counts[origin_court]["duplicate_sentence_id_skipped"] += 1
            duplicate_breakdown["duplicate_sentence_id"] += 1
            continue
        seen_sentence_ids.add(sentence_id)
        unique_candidates.append(candidate)

    manifest_path = merged_root / "manifest.jsonl"
    with manifest_path.open("w", encoding="utf-8") as manifest_fh:
        for idx, record in enumerate(unique_candidates, start=1):
            _copy_record_to_authoritative_corpus(
                merged_root=merged_root,
                manifest_fh=manifest_fh,
                record=record,
                full_text=_normalize_space(record.get("full_text")),
                index=idx,
            )

    duplicates_total = duplicate_breakdown.get("duplicate_sentence_id", 0)
    return MergeStats(
        per_court_counts=per_court_counts,
        merged_candidate_total=len(candidates),
        merged_after_dedupe_total=len(unique_candidates),
        duplicates_total=duplicates_total,
        duplicates_by_reason=duplicate_breakdown,
    )


def _build_metadata_attachment_policy_summary(
    *,
    merged_manifest_path: Path,
    model_metadata_path: Path,
    baseline_metadata_path: Path,
) -> dict[str, Any]:
    """Define authoritative post-merge metadata attachment policy.

    Policy is evaluated on the merged/deduped manifest instead of per-court raw runs:
    - prefer model-generated metadata when available
    - fallback to deterministic baseline when model metadata is unavailable
    - do not remove deterministic baseline because it also acts as regression guard
    """

    merged_rows = read_manifest(merged_manifest_path)
    selected_model = resolve_model_metadata_path(
        model_metadata_path,
        default_path=DEFAULT_MODEL_METADATA_PATH,
        explicit_override=(model_metadata_path != DEFAULT_MODEL_METADATA_PATH),
    )
    model_index = _build_metadata_index(selected_model.path)
    baseline_index = _build_metadata_index(baseline_metadata_path)

    model_preferred = 0
    baseline_fallback = 0
    unresolved = 0

    for row in merged_rows:
        case_number = _normalize_space(row.get("authoritative_case_number"))
        if not case_number:
            unresolved += 1
            continue
        if case_number in model_index:
            model_preferred += 1
        elif case_number in baseline_index:
            baseline_fallback += 1
        else:
            unresolved += 1

    return {
        "attachment_stage": "post_merge_authoritative_corpus",
        "selected_model_metadata_path": selected_model.path.as_posix(),
        "selected_model_metadata_case_count": selected_model.case_count,
        "baseline_metadata_path": baseline_metadata_path.as_posix(),
        "baseline_metadata_case_count": len(baseline_index),
        "policy": {
            "preferred_source": "model_generated",
            "fallback_source": "deterministic_baseline",
            "deterministic_baseline_retained": True,
            "metadata_generation_in_day59": "not_regenerated",
            "default_local_model_policy": "unchanged (qwen2.5:3b-instruct)",
        },
        "coverage_estimate_on_merged_manifest": {
            "merged_cases": len(merged_rows),
            "model_preferred_cases": model_preferred,
            "deterministic_fallback_cases": baseline_fallback,
            "unresolved_cases": unresolved,
        },
    }


def _write_outputs(
    *,
    merged_root: Path,
    court_summaries: list[CourtRunSummary],
    merge_stats: MergeStats,
    metadata_policy_summary: dict[str, Any],
) -> dict[str, Any]:
    output = {
        "day": 60,
        "authoritative_flow": [
            "per_court_convergence_crawl",
            "merge_and_dedupe",
            "downstream_retrieval_consumption",
            "attach_preferred_metadata",
            "deterministic_fallback_when_needed",
        ],
        "court_runs": [asdict(item) for item in court_summaries],
        "merge_stats": asdict(merge_stats),
        "metadata_attachment_policy_summary": metadata_policy_summary,
    }

    report_json = merged_root / "full_corpus_merge_report.json"
    report_txt = merged_root / "full_corpus_merge_report.txt"
    report_json.write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    txt_lines = [
        "Day 60 Full Corpus Assembly Report",
        "================================",
        "authoritative flow: per-court convergence crawl -> merge/dedupe -> retrieval -> metadata attach",
        "",
        "per-court raw counts:",
    ]
    for item in court_summaries:
        txt_lines.append(
            f"- {item.court}: raw={item.raw_records}, with_sentence_id={item.candidates_with_sentence_id}, "
            f"missing_sentence_id_skipped={item.missing_sentence_id_skipped}, "
            f"duplicate_sentence_id_skipped={item.duplicate_sentence_id_skipped}, "
            f"rounds_run={item.rounds_run}, "
            f"total_unique_sentence_id_discovered={item.total_unique_sentence_id_discovered}, "
            f"new_corpus_records_added={item.new_corpus_records_added}, "
            f"convergence_stop_reason={item.convergence_stop_reason or 'n/a'} "
            f"(manifest: {item.manifest_path})"
        )

    txt_lines.extend(
        [
            "",
            f"merged candidate total: {merge_stats.merged_candidate_total}",
            f"merged after dedupe total: {merge_stats.merged_after_dedupe_total}",
            f"duplicates total: {merge_stats.duplicates_total}",
            "duplicate reason breakdown:",
            f"- duplicate_sentence_id: {merge_stats.duplicates_by_reason.get('duplicate_sentence_id', 0)}",
            f"- missing_sentence_id_skipped: {merge_stats.duplicates_by_reason.get('missing_sentence_id_skipped', 0)}",
            "",
            "metadata attachment stage policy:",
            "- attach after authoritative merge/dedupe (not per-court crawl)",
            "- prefer model-generated metadata; fallback to deterministic baseline",
            "- deterministic baseline retained for fallback/benchmark/regression guard",
            "- default local model policy unchanged (qwen2.5:3b-instruct)",
        ]
    )
    report_txt.write_text("\n".join(txt_lines) + "\n", encoding="utf-8")

    return output


def main() -> int:
    args = parse_args()
    courts = [c.strip().lower() for c in args.courts if c.strip()]
    if not courts:
        raise ValueError("At least one court must be provided via --courts")

    manifest_overrides = _parse_explicit_manifest_overrides(args.court_manifest)

    court_manifest_paths: dict[str, Path] = {}
    child_run_summaries: dict[str, dict[str, Any]] = {}
    all_candidates: list[dict[str, Any]] = []

    for court in courts:
        if court not in COURTS:
            raise ValueError(f"Unsupported court mode: {court}; supported: {', '.join(COURTS)}")

        if court in manifest_overrides:
            manifest_path = manifest_overrides[court]
            child_run_summaries[court] = {}
        elif args.skip_crawl:
            raise ValueError(f"--skip-crawl requires --court-manifest for court={court}")
        else:
            manifest_path, child_summary = _run_per_court_crawl(args, court)
            child_run_summaries[court] = child_summary

        records = _collect_merge_candidates(manifest_path=manifest_path, court=court)
        court_manifest_paths[court] = manifest_path
        all_candidates.extend(records)
        with_sentence_id = sum(1 for row in records if _normalize_space(row.get("sentence_id")))
        missing_sentence_id = len(records) - with_sentence_id
        print(f"[day59] per-court raw candidate count {court}: {len(records)}")
        print(f"[day59] per-court candidates with sentence_id {court}: {with_sentence_id}")
        print(f"[day59] per-court missing_sentence_id skipped (pre-merge estimate) {court}: {missing_sentence_id}")
        if child_run_summaries.get(court):
            child = child_run_summaries[court]
            print(
                f"[day60] convergence summary {court}: rounds={child.get('total_rounds_run', 0)}, "
                f"new_sentence_ids={child.get('total_unique_sentence_id_discovered', 0)}, "
                f"new_corpus_records={child.get('new_corpus_records_added', 0)}, "
                f"stop={child.get('convergence_stop_reason', 'n/a')}"
            )

    merge_stats = _dedupe_and_write_authoritative_corpus(candidates=all_candidates, merged_root=args.merged_root)
    court_summaries: list[CourtRunSummary] = []
    for court in courts:
        stats = merge_stats.per_court_counts.get(
            court,
            {
                "raw_candidates": 0,
                "candidates_with_sentence_id": 0,
                "missing_sentence_id_skipped": 0,
                "duplicate_sentence_id_skipped": 0,
            },
        )
        court_summaries.append(
            CourtRunSummary(
                court=court,
                manifest_path=court_manifest_paths[court].as_posix(),
                raw_records=stats["raw_candidates"],
                candidates_with_sentence_id=stats["candidates_with_sentence_id"],
                missing_sentence_id_skipped=stats["missing_sentence_id_skipped"],
                duplicate_sentence_id_skipped=stats["duplicate_sentence_id_skipped"],
                rounds_run=int(child_run_summaries.get(court, {}).get("total_rounds_run", 0) or 0),
                total_unique_sentence_id_discovered=int(
                    child_run_summaries.get(court, {}).get("total_unique_sentence_id_discovered", 0) or 0
                ),
                new_corpus_records_added=int(child_run_summaries.get(court, {}).get("new_corpus_records_added", 0) or 0),
                convergence_stop_reason=str(child_run_summaries.get(court, {}).get("convergence_stop_reason") or ""),
            )
        )
        print(f"[day59] per-court duplicate_sentence_id skipped {court}: {stats['duplicate_sentence_id_skipped']}")

    metadata_summary = _build_metadata_attachment_policy_summary(
        merged_manifest_path=args.merged_root / "manifest.jsonl",
        model_metadata_path=args.model_metadata,
        baseline_metadata_path=args.baseline_metadata,
    )
    result = _write_outputs(
        merged_root=args.merged_root,
        court_summaries=court_summaries,
        merge_stats=merge_stats,
        metadata_policy_summary=metadata_summary,
    )

    print(f"[day59] merged candidate total: {merge_stats.merged_candidate_total}")
    print(f"[day59] merged authoritative total: {merge_stats.merged_after_dedupe_total}")
    print(f"[day59] duplicates total: {merge_stats.duplicates_total}")
    print(f"[day59] duplicate breakdown: {merge_stats.duplicates_by_reason}")
    print(f"[day59] merged manifest: {(args.merged_root / 'manifest.jsonl').as_posix()}")
    print(f"[day59] report json: {(args.merged_root / 'full_corpus_merge_report.json').as_posix()}")

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
