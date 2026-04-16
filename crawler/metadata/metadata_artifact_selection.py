#!/usr/bin/env python3
"""Utilities for selecting local model-generated metadata artifacts."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

LATEST_SENTINEL = "latest"
DIGEST_FIELDS = ("case_summary", "holding", "legal_basis", "disputed_issues")


@dataclass(frozen=True)
class MetadataArtifactCandidate:
    path: Path
    case_count: int
    modified_time: float
    parseable: bool
    schema_compatible: bool
    has_report_pair: bool

    @property
    def is_valid(self) -> bool:
        return self.parseable and self.schema_compatible and self.case_count > 0


@dataclass(frozen=True)
class SelectedMetadataArtifact:
    path: Path
    case_count: int
    modified_time: float
    source: str


def _load_jsonl_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file_obj:
        for line_no, line in enumerate(file_obj, start=1):
            text = line.strip()
            if not text:
                continue
            try:
                payload = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL row in {path} line {line_no}: {exc}") from exc
            if not isinstance(payload, dict):
                raise ValueError(f"Invalid JSONL row in {path} line {line_no}: expected object")
            rows.append(payload)
    return rows


def _extract_case_number(payload: dict[str, Any]) -> str:
    core = payload.get("core_case_metadata") if isinstance(payload.get("core_case_metadata"), dict) else {}
    return str(
        core.get("authoritative_case_number")
        or payload.get("authoritative_case_number")
        or payload.get("case_number")
        or ""
    ).strip()


def _schema_compatible(payload: dict[str, Any]) -> bool:
    generated = payload.get("generated_digest_metadata")
    digest = generated if isinstance(generated, dict) else payload
    return any(field in digest for field in DIGEST_FIELDS)


def inspect_metadata_artifact(path: Path) -> MetadataArtifactCandidate:
    if not path.exists() or not path.is_file():
        return MetadataArtifactCandidate(
            path=path,
            case_count=0,
            modified_time=0.0,
            parseable=False,
            schema_compatible=False,
            has_report_pair=False,
        )

    report_pair = path.with_name(path.stem + "_report.txt").exists() or path.with_name(
        path.stem + "_generation_report.txt"
    ).exists()

    try:
        rows = _load_jsonl_rows(path)
    except ValueError:
        return MetadataArtifactCandidate(
            path=path,
            case_count=0,
            modified_time=path.stat().st_mtime,
            parseable=False,
            schema_compatible=False,
            has_report_pair=report_pair,
        )

    valid_cases: set[str] = set()
    schema_hits = 0
    for payload in rows:
        case_number = _extract_case_number(payload)
        if case_number:
            valid_cases.add(case_number)
        if _schema_compatible(payload):
            schema_hits += 1

    return MetadataArtifactCandidate(
        path=path,
        case_count=len(valid_cases),
        modified_time=path.stat().st_mtime,
        parseable=True,
        schema_compatible=schema_hits > 0,
        has_report_pair=report_pair,
    )


def _name_priority(path: Path) -> int:
    name = path.name
    if "expanded_current_default_model_generation_batch_output" in name:
        return 3
    if name.startswith("model_output__"):
        return 2
    if "model_generated_metadata_output" in name:
        return 1
    return 0


def discover_model_metadata_candidates() -> list[Path]:
    patterns = [
        Path("data/eval/expanded_current_default_model_generation_batch_output.jsonl"),
        Path("data/eval/model_generated_metadata_output.jsonl"),
        Path("data/eval/metadata_prompt_eval_loop/model_output__*.jsonl"),
    ]

    candidates: list[Path] = []
    seen: set[Path] = set()
    for pattern in patterns:
        if "*" in str(pattern):
            for item in Path().glob(str(pattern)):
                if item.is_file() and item not in seen:
                    seen.add(item)
                    candidates.append(item)
            continue
        if pattern.exists() and pattern.is_file() and pattern not in seen:
            seen.add(pattern)
            candidates.append(pattern)
    return candidates


def select_latest_valid_model_metadata(candidates: list[Path] | None = None) -> SelectedMetadataArtifact:
    pool = candidates if candidates is not None else discover_model_metadata_candidates()

    inspected = [inspect_metadata_artifact(item) for item in pool]
    valid = [item for item in inspected if item.is_valid]
    if not valid:
        raise FileNotFoundError("No valid model-generated metadata artifact found.")

    selected = max(
        valid,
        key=lambda item: (
            item.modified_time,
            _name_priority(item.path),
            1 if item.has_report_pair else 0,
            item.path.as_posix(),
        ),
    )
    return SelectedMetadataArtifact(
        path=selected.path,
        case_count=selected.case_count,
        modified_time=selected.modified_time,
        source="auto_latest",
    )


def resolve_model_metadata_path(
    requested_path: Path,
    *,
    default_path: Path,
    explicit_override: bool = False,
) -> SelectedMetadataArtifact:
    requested_raw = str(requested_path).strip()
    is_latest_sentinel = requested_raw.lower() == LATEST_SENTINEL

    if is_latest_sentinel:
        return select_latest_valid_model_metadata()

    if explicit_override or requested_path != default_path:
        inspected = inspect_metadata_artifact(requested_path)
        if not inspected.is_valid:
            raise FileNotFoundError(
                "Explicit model metadata path is not a valid output: "
                f"{requested_path} (exists={requested_path.exists()}, parseable={inspected.parseable}, "
                f"schema_compatible={inspected.schema_compatible}, case_count={inspected.case_count})"
            )
        return SelectedMetadataArtifact(
            path=requested_path,
            case_count=inspected.case_count,
            modified_time=inspected.modified_time,
            source="explicit_path",
        )

    if requested_path.exists():
        inspected_default = inspect_metadata_artifact(requested_path)
        if inspected_default.is_valid:
            latest = select_latest_valid_model_metadata()
            if latest.path == requested_path:
                return SelectedMetadataArtifact(
                    path=requested_path,
                    case_count=inspected_default.case_count,
                    modified_time=inspected_default.modified_time,
                    source="default_path_valid",
                )

    latest = select_latest_valid_model_metadata()
    return latest
