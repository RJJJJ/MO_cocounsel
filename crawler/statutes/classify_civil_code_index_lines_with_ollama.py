#!/usr/bin/env python3
"""Classify Civil Code index lines into constrained node_type taxonomy with Ollama."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import Request, urlopen

INPUT_PATH = Path("data/parsed/statutes/civil_code/index/index_lines.jsonl")
OUTPUT_PATH = Path("data/parsed/statutes/civil_code/index/index_lines_classified.jsonl")
REPORT_PATH = Path("data/parsed/statutes/civil_code/index/index_lines_classification_report.json")
SYSTEM_PROMPT_PATH = Path("prompts/statutes/civil_code_index_line_classifier_system.txt")
USER_PROMPT_TEMPLATE_PATH = Path("prompts/statutes/civil_code_index_line_classifier_user.txt")
ALLOWED_TYPES = {"part", "chapter", "section", "article", "heading", "noise"}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file_obj:
        for raw in file_obj:
            raw = raw.strip()
            if not raw:
                continue
            rows.append(json.loads(raw))
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_obj:
        for row in rows:
            file_obj.write(json.dumps(row, ensure_ascii=False) + "\n")


def normalize_line_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.replace("\u3000", " ")).strip()


def heuristic_classification(text: str) -> tuple[str, float, bool, str]:
    normalized = normalize_line_text(text)
    if not normalized:
        return "noise", 0.99, False, normalized

    lowered = normalized.lower()
    if re.search(r"^livro\b|^parte\b|^part\b", lowered):
        return "part", 0.74, True, normalized
    if re.search(r"^t[ií]tulo\b|^cap[ií]tulo\b|^chapter\b", lowered):
        return "chapter", 0.72, True, normalized
    if re.search(r"^sec[cç][aã]o\b|^secção\b|^section\b", lowered):
        return "section", 0.72, True, normalized
    if re.search(r"^art\.?\s*\d+|^artigo\s+\d+", lowered):
        return "article", 0.88, False, normalized
    if len(normalized) <= 2:
        return "noise", 0.95, False, normalized
    if re.search(r"índice|indice|civil|código|codigo|boletim", lowered):
        return "heading", 0.58, True, normalized
    return "heading", 0.52, True, normalized


def render_user_prompt(template: str, line_no: int, line_text: str) -> str:
    return template.replace("{{line_no}}", str(line_no)).replace("{{line_text}}", line_text)


def call_ollama(
    *,
    model: str,
    system_prompt: str,
    user_prompt: str,
    host: str,
    timeout_seconds: int,
) -> str:
    payload = {
        "model": model,
        "system": system_prompt,
        "prompt": user_prompt,
        "stream": False,
        "format": "json",
        "options": {
            "temperature": 0,
            "top_p": 0.1,
        },
    }
    request = Request(
        f"{host.rstrip('/')}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310
        result = json.loads(response.read().decode("utf-8", errors="replace"))
    return str(result.get("response", "")).strip()


def parse_model_output(raw: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[\s\S]*\}", raw)
    if not match:
        raise ValueError("model_output_missing_json")
    return json.loads(match.group(0))


def sanitize_classification(result: dict[str, Any], original_text: str) -> tuple[str, float, bool, str, str]:
    proposed_type = str(result.get("node_type", "noise")).strip().lower()
    node_type = proposed_type if proposed_type in ALLOWED_TYPES else "noise"

    confidence = result.get("confidence", 0.5)
    if not isinstance(confidence, (int, float)):
        confidence = 0.5
    confidence = max(0.0, min(1.0, float(confidence)))

    repaired_line = normalize_line_text(str(result.get("repaired_line", original_text)))
    rationale = normalize_line_text(str(result.get("rationale", "")))
    needs_review = bool(result.get("needs_review", confidence < 0.65 or node_type == "noise"))
    return node_type, confidence, needs_review, repaired_line or normalize_line_text(original_text), rationale


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Classify Civil Code index lines with Ollama.")
    parser.add_argument("--input-path", type=Path, default=INPUT_PATH)
    parser.add_argument("--output-path", type=Path, default=OUTPUT_PATH)
    parser.add_argument("--report-path", type=Path, default=REPORT_PATH)
    parser.add_argument("--system-prompt-path", type=Path, default=SYSTEM_PROMPT_PATH)
    parser.add_argument("--user-prompt-template-path", type=Path, default=USER_PROMPT_TEMPLATE_PATH)
    parser.add_argument("--model", default="qwen3:4b-instruct")
    parser.add_argument("--ollama-host", default="http://127.0.0.1:11434")
    parser.add_argument("--timeout-seconds", type=int, default=45)
    parser.add_argument("--max-lines", type=int, default=0)
    parser.add_argument("--no-ollama", action="store_true", help="Use deterministic heuristics only.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    rows = load_jsonl(args.input_path)
    if args.max_lines > 0:
        rows = rows[: args.max_lines]

    system_prompt = args.system_prompt_path.read_text(encoding="utf-8")
    user_prompt_template = args.user_prompt_template_path.read_text(encoding="utf-8")

    out_rows: list[dict[str, Any]] = []
    stats_by_type = {key: 0 for key in sorted(ALLOWED_TYPES)}
    used_heuristic = 0
    used_ollama = 0

    for row in rows:
        line_no = int(row.get("line_no", 0))
        line_text = normalize_line_text(str(row.get("line_text", "")))
        source_url = str(row.get("source_url", ""))
        href = str(row.get("href", ""))

        node_type, confidence, needs_review, repaired_line, rationale = heuristic_classification(line_text)
        method = "heuristic"

        if not args.no_ollama:
            prompt = render_user_prompt(user_prompt_template, line_no=line_no, line_text=line_text)
            try:
                raw = call_ollama(
                    model=args.model,
                    system_prompt=system_prompt,
                    user_prompt=prompt,
                    host=args.ollama_host,
                    timeout_seconds=args.timeout_seconds,
                )
                parsed = parse_model_output(raw)
                node_type, confidence, needs_review, repaired_line, rationale = sanitize_classification(parsed, line_text)
                method = "ollama"
                used_ollama += 1
            except (TimeoutError, URLError, ValueError, json.JSONDecodeError):
                method = "heuristic_fallback"
                used_heuristic += 1
        else:
            used_heuristic += 1

        stats_by_type[node_type] = stats_by_type.get(node_type, 0) + 1

        out_rows.append(
            {
                "line_no": line_no,
                "line_text": line_text,
                "repaired_line": repaired_line,
                "source_url": source_url,
                "href": href,
                "node_type": node_type,
                "confidence": round(confidence, 4),
                "needs_review": needs_review,
                "classification_method": method,
                "rationale": rationale,
            }
        )

    write_jsonl(args.output_path, out_rows)

    report = {
        "input_path": str(args.input_path),
        "output_path": str(args.output_path),
        "line_count": len(out_rows),
        "counts_by_node_type": stats_by_type,
        "ollama_model": args.model,
        "ollama_used_count": used_ollama,
        "heuristic_used_count": used_heuristic,
        "allowed_node_types": sorted(ALLOWED_TYPES),
    }
    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
