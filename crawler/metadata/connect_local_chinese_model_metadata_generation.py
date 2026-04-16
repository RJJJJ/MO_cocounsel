#!/usr/bin/env python3
"""Day 43: connect local Chinese model metadata generation to comparison harness.

Scope constraints:
- local-only
- no database
- no external/cloud API
- no vector retrieval

This script builds model-generated metadata records for selected sample cases and writes
Day 38-compatible JSONL rows for Day 42 comparison harness input.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

DEFAULT_INPUT_PATH = Path("data/corpus/prepared/macau_court_cases/bm25_chunks.jsonl")
DEFAULT_OUTPUT_PATH = Path("data/eval/model_generated_metadata_output.jsonl")
DEFAULT_REPORT_PATH = Path("data/eval/local_model_metadata_generation_report.txt")
DEFAULT_SAMPLE_CASE_LIMIT = 5
DEFAULT_LANGUAGE = "zh"
DEFAULT_MODEL_NAME = os.getenv("LOCAL_METADATA_MODEL_NAME", "qwen2.5:7b-instruct")
DEFAULT_PROMPT_VERSION = os.getenv("LOCAL_METADATA_PROMPT_VERSION", "day43_local_model_metadata_v1")
DEFAULT_BACKEND = os.getenv("LOCAL_MODEL_BACKEND", "ollama_cli")
DEFAULT_TIMEOUT_SECONDS = int(os.getenv("LOCAL_MODEL_TIMEOUT_SECONDS", "180"))

GENERATION_FIELDS = ["case_summary", "holding", "legal_basis", "disputed_issues"]


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


class LocalModelRunner:
    def __init__(self, backend: str, model_name: str, timeout_seconds: int, command_template: str | None) -> None:
        self.backend = backend
        self.model_name = model_name
        self.timeout_seconds = timeout_seconds
        self.command_template = command_template

    def run(self, prompt: str) -> str:
        if self.backend == "ollama_cli":
            return self._run_ollama_cli(prompt)
        if self.backend == "command":
            return self._run_command_template(prompt)
        raise ValueError(f"Unsupported backend: {self.backend}")

    def _run_ollama_cli(self, prompt: str) -> str:
        completed = subprocess.run(
            ["ollama", "run", self.model_name, prompt],
            capture_output=True,
            text=True,
            timeout=self.timeout_seconds,
            check=False,
        )
        if completed.returncode != 0:
            raise RuntimeError(f"ollama run failed: {completed.stderr.strip() or completed.stdout.strip()}")
        return completed.stdout.strip()

    def _run_command_template(self, prompt: str) -> str:
        if not self.command_template:
            raise ValueError("--command-template is required when --backend command is used")

        with NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=True) as temp_prompt:
            temp_prompt.write(prompt)
            temp_prompt.flush()
            command = self.command_template.format(model=self.model_name, prompt_file=temp_prompt.name)
            completed = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )

        if completed.returncode != 0:
            raise RuntimeError(f"local command failed: {completed.stderr.strip() or completed.stdout.strip()}")
        return completed.stdout.strip()


def normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u3000", " ")).strip()


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
            except Exception as exc:
                raise ValueError(f"Invalid row at line {line_no}: {exc}") from exc
    return chunks


def group_chunks_by_case(chunks: list[CaseChunk]) -> dict[str, list[CaseChunk]]:
    grouped: dict[str, list[CaseChunk]] = defaultdict(list)
    for chunk in chunks:
        grouped[chunk.authoritative_case_number or "UNKNOWN_CASE"].append(chunk)
    return dict(grouped)


def select_cases(
    grouped: dict[str, list[CaseChunk]],
    sample_case_limit: int,
    language: str,
    explicit_case_numbers: list[str],
) -> list[tuple[str, list[CaseChunk]]]:
    ordered = sorted(grouped.items(), key=lambda item: item[0])

    if explicit_case_numbers:
        number_set = set(explicit_case_numbers)
        selected = [(num, chunks) for num, chunks in ordered if num in number_set]
        return selected[: max(sample_case_limit, 1)]

    selected: list[tuple[str, list[CaseChunk]]] = []
    for case_number, case_chunks in ordered:
        head_language = case_chunks[0].language.lower().strip()
        if language and head_language != language:
            continue
        selected.append((case_number, case_chunks))
        if len(selected) >= max(sample_case_limit, 1):
            break
    return selected


def build_prompt(case_chunks: list[CaseChunk], prompt_version: str, max_input_chars: int) -> str:
    head = case_chunks[0]
    chunk_text = normalize_whitespace(" ".join(chunk.chunk_text for chunk in case_chunks))
    clipped_text = chunk_text[:max_input_chars]

    return (
        "你是法律判決摘要與結構化資訊抽取助手。"
        "請根據以下案件文本，僅輸出 JSON，不要輸出其他文字。\\n"
        f"prompt_version: {prompt_version}\\n"
        "JSON 結構必須包含這四個欄位："
        "case_summary (string), holding (string), legal_basis (string array), disputed_issues (string array)。\\n"
        "要求：\\n"
        "1) 使用繁體中文；\\n"
        "2) 內容要精簡但忠於文本；\\n"
        "3) legal_basis 只填在文本中可辨識的法條或法律依據；\\n"
        "4) 如果資訊不足，請使用空字串或空陣列。\\n"
        f"案件編號: {head.authoritative_case_number}\\n"
        f"案件語言: {head.language}\\n"
        f"案件類型: {head.case_type}\\n"
        "案件文本：\\n"
        f"{clipped_text}"
    )


def _extract_first_json_block(raw: str) -> dict[str, Any]:
    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        raise ValueError("Model output did not contain a JSON object")
    candidate = match.group(0)
    return json.loads(candidate)


def _ensure_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        parts = re.split(r"[、，,;；\n]+", value)
        return [p.strip() for p in parts if p.strip()]
    return []


def sanitize_generated_fields(raw_payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_summary": str(raw_payload.get("case_summary", "")).strip(),
        "holding": str(raw_payload.get("holding", "")).strip(),
        "legal_basis": _ensure_string_list(raw_payload.get("legal_basis", [])),
        "disputed_issues": _ensure_string_list(raw_payload.get("disputed_issues", [])),
    }


def build_output_record(
    case_chunks: list[CaseChunk],
    generated_fields: dict[str, Any],
    generation_status: str,
    model_name: str,
    prompt_version: str,
    notes: list[str],
) -> dict[str, Any]:
    head = case_chunks[0]
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
                {path for path in [head.source_metadata_path, head.source_full_text_path] if path}
            ),
        },
        "generated_digest_metadata": generated_fields,
        "generation_status": generation_status,
        "generation_method": "local_model_generated",
        "model_name": model_name,
        "prompt_version": prompt_version,
        "provenance_notes": notes,
    }


def write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_obj:
        for record in records:
            file_obj.write(json.dumps(record, ensure_ascii=False) + "\n")


def build_report(
    *,
    input_path: Path,
    output_path: Path,
    selected_case_numbers: list[str],
    records: list[dict[str, Any]],
    success_count: int,
    fail_count: int,
    generation_fields: list[str],
    model_name: str,
    prompt_version: str,
    backend: str,
) -> str:
    overall_success = len(records) > 0 and success_count > 0
    lines = [
        "Local Model Metadata Generation Report - Day 43",
        f"input_chunks_path: {input_path}",
        f"output_jsonl_path: {output_path}",
        f"model_backend: {backend}",
        f"model_name: {model_name}",
        f"prompt_version: {prompt_version}",
        f"sample cases selected: {len(selected_case_numbers)}",
        f"sample case numbers: {selected_case_numbers}",
        f"model-generated cases written: {len(records)}",
        f"generation success count: {success_count}",
        f"generation failure count: {fail_count}",
        f"generation fields attempted: {generation_fields}",
        "whether local model metadata generation appears successful: "
        f"{overall_success}",
        "",
        "Sample outputs:",
    ]
    for idx, item in enumerate(records[:3], start=1):
        lines.append(f"\n=== sample_case_{idx} ===")
        lines.append(json.dumps(item, ensure_ascii=False, indent=2))
    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Connect local Chinese model metadata generation (Day 43).")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH)
    parser.add_argument("--sample-case-limit", type=int, default=DEFAULT_SAMPLE_CASE_LIMIT)
    parser.add_argument("--language", default=DEFAULT_LANGUAGE, help="Language filter, e.g. zh / pt / ''.")
    parser.add_argument(
        "--case-numbers",
        default="",
        help="Comma-separated authoritative case numbers for explicit sample selection.",
    )
    parser.add_argument("--model-name", default=DEFAULT_MODEL_NAME)
    parser.add_argument("--prompt-version", default=DEFAULT_PROMPT_VERSION)
    parser.add_argument("--backend", choices=["ollama_cli", "command"], default=DEFAULT_BACKEND)
    parser.add_argument(
        "--command-template",
        default=os.getenv("LOCAL_MODEL_COMMAND_TEMPLATE", ""),
        help="Used when --backend command. Template vars: {model}, {prompt_file}",
    )
    parser.add_argument("--timeout-seconds", type=int, default=DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--max-input-chars", type=int, default=6000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Input chunks file not found: {args.input}")

    chunks = load_chunks(args.input)
    grouped = group_chunks_by_case(chunks)
    explicit_case_numbers = [item.strip() for item in args.case_numbers.split(",") if item.strip()]
    selected = select_cases(
        grouped=grouped,
        sample_case_limit=args.sample_case_limit,
        language=args.language.strip().lower(),
        explicit_case_numbers=explicit_case_numbers,
    )

    runner = LocalModelRunner(
        backend=args.backend,
        model_name=args.model_name,
        timeout_seconds=max(args.timeout_seconds, 1),
        command_template=args.command_template.strip() or None,
    )

    records: list[dict[str, Any]] = []
    success_count = 0
    fail_count = 0

    for _, case_chunks in selected:
        prompt = build_prompt(case_chunks, prompt_version=args.prompt_version, max_input_chars=args.max_input_chars)
        notes = [
            "Local-only generation path.",
            "No cloud API/database used.",
            f"backend={args.backend}",
        ]
        generation_status = "local_model_generation_failed"
        generated_fields = {
            "case_summary": "",
            "holding": "",
            "legal_basis": [],
            "disputed_issues": [],
        }

        try:
            raw_output = runner.run(prompt)
            parsed = _extract_first_json_block(raw_output)
            generated_fields = sanitize_generated_fields(parsed)
            generation_status = "local_model_generated"
            success_count += 1
        except Exception as exc:
            fail_count += 1
            notes.append(f"generation_error={exc}")

        record = build_output_record(
            case_chunks=case_chunks,
            generated_fields=generated_fields,
            generation_status=generation_status,
            model_name=args.model_name,
            prompt_version=args.prompt_version,
            notes=notes,
        )
        records.append(record)

    write_jsonl(args.output, records)

    report_text = build_report(
        input_path=args.input,
        output_path=args.output,
        selected_case_numbers=[case_number for case_number, _ in selected],
        records=records,
        success_count=success_count,
        fail_count=fail_count,
        generation_fields=GENERATION_FIELDS,
        model_name=args.model_name,
        prompt_version=args.prompt_version,
        backend=args.backend,
    )
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(report_text, encoding="utf-8")

    # Required terminal lines.
    print(f"sample cases selected: {len(selected)}")
    print(f"sample case numbers: {[case_number for case_number, _ in selected]}")
    print(f"model-generated cases written: {len(records)}")
    print(f"generation fields attempted: {GENERATION_FIELDS}")
    print(
        "whether local model metadata generation appears successful: "
        f"{len(records) > 0 and success_count > 0}"
    )
    print(f"output written: {args.output}")
    print(f"report written: {args.report}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
