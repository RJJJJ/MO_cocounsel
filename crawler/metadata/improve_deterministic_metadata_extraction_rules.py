#!/usr/bin/env python3
"""Day 41: improve deterministic metadata extraction rules from Day 40 eval feedback.

Priorities:
- primary: case_summary
- secondary: holding
- keep strong fields stable: legal_basis, disputed_issues

Scope constraints:
- local-only
- no database
- no external API
- no LLM
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_INPUT_PATH = Path("data/corpus/prepared/macau_court_cases/bm25_chunks.jsonl")
DEFAULT_OUTPUT_PATH = Path("data/eval/deterministic_metadata_extraction_improved_output.jsonl")
DEFAULT_REPORT_PATH = Path("data/eval/deterministic_metadata_extraction_improved_report.txt")
DEFAULT_SAMPLE_CASES_IN_REPORT = 3


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
            except Exception as exc:  # pragma: no cover - defensive local guard
                raise ValueError(f"Invalid row at line {line_no}: {exc}") from exc
    return chunks


def group_chunks_by_case(chunks: list[CaseChunk]) -> dict[str, list[CaseChunk]]:
    grouped: dict[str, list[CaseChunk]] = defaultdict(list)
    for chunk in chunks:
        case_number = chunk.authoritative_case_number or "UNKNOWN_CASE"
        grouped[case_number].append(chunk)
    return dict(grouped)


def normalize_whitespace(text: str) -> str:
    text = text.replace("\u3000", " ")
    return re.sub(r"\s+", " ", text).strip()


def split_sentences(text: str) -> list[str]:
    if not text:
        return []
    pieces = re.split(r"(?<=[。.!?；;])\s+", text)
    return [p.strip() for p in pieces if p.strip()]


def clip(text: str, max_chars: int) -> str:
    cleaned = normalize_whitespace(text)
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3] + "..."


def split_issue_candidates(raw: str) -> list[str]:
    candidates = re.split(r"[、，,;；]+", raw)
    return [normalize_whitespace(item).strip("-:：.。 ") for item in candidates if normalize_whitespace(item)]


def first_heading_value(text: str, heading_patterns: list[str], max_len: int = 220) -> str:
    compiled = [re.compile(rf"(?:^|\s)(?:{pattern})\s*[:：]\s*(.+)", flags=re.IGNORECASE) for pattern in heading_patterns]
    for raw_line in text.splitlines():
        line = normalize_whitespace(raw_line)
        if not line:
            continue
        for regex in compiled:
            match = regex.search(line)
            if not match:
                continue
            value = normalize_whitespace(match.group(1))
            value = re.sub(r"^[\-•‧·]+", "", value).strip()
            if value:
                return clip(value, max_len)
    return ""


def extract_heading_block(text: str, heading_patterns: list[str], stop_patterns: list[str]) -> str:
    if not text:
        return ""

    starts: list[int] = []
    for pattern in heading_patterns:
        match = re.search(rf"{pattern}\s*[:：]?", text, flags=re.IGNORECASE)
        if match:
            starts.append(match.end())
    if not starts:
        return ""

    start = min(starts)
    stop = len(text)
    for pattern in stop_patterns:
        match = re.search(rf"{pattern}\s*[:：]?", text[start:], flags=re.IGNORECASE)
        if match:
            stop = min(stop, start + match.start())

    if stop <= start:
        return ""
    return normalize_whitespace(text[start:stop])


def normalize_summary_sentence(sentence: str, language: str) -> str:
    cleaned = normalize_whitespace(sentence)
    if not cleaned:
        return ""

    cleaned = re.sub(r"（[^）]{0,80}參見[^）]*）", "", cleaned)
    cleaned = re.sub(r"\([^\)]{0,80}cf\.[^\)]*\)", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^[IVXLCM]+\s*[\-–—.]\s*", "", cleaned)
    cleaned = re.sub(r"^\d+\s*[\-–—.)]\s*", "", cleaned)
    cleaned = re.sub(r"^\*+\s*", "", cleaned)
    cleaned = normalize_whitespace(cleaned)

    if language == "zh":
        cleaned = cleaned.replace("裁判摘要", "").strip(" ：")
    else:
        cleaned = re.sub(r"^(sum[áa]rio|resumo)\s*", "", cleaned, flags=re.IGNORECASE)

    return cleaned


def extract_case_summary(language: str, text: str, case_type: str) -> str:
    cleaned = normalize_whitespace(text)
    if not cleaned:
        return ""

    if language == "zh":
        issue_line = first_heading_value(cleaned, [r"主要問題", r"重要法律問題", r"主題"])
        if issue_line:
            terms = split_issue_candidates(issue_line)
            if terms:
                return clip(f"本案聚焦{'、'.join(terms)}。", 220)

        block = extract_heading_block(
            cleaned,
            heading_patterns=[r"裁判摘要", r"摘要", r"摘\s*要", r"案情摘要"],
            stop_patterns=[r"裁判書製作人", r"澳門特別行政區", r"一、", r"二、", r"三、", r"事實", r"理由說明", r"裁判"],
        )
    else:
        issue_line = first_heading_value(cleaned, [r"Assunto", r"Descritores"])
        if issue_line:
            terms = split_issue_candidates(issue_line)
            if terms:
                return clip(f"O caso discute {'; '.join(terms)}.", 240)

        block = extract_heading_block(
            cleaned,
            heading_patterns=[r"SUM[ÁA]RIO", r"RESUMO"],
            stop_patterns=[r"O\s+Relator", r"ACORDAM", r"I\.?\s+RELAT[ÓO]RIO", r"II\.", r"DECIS[ÃA]O", r"FUNDAMENTA[CÇ][ÃA]O"],
        )

    if block:
        sentences = [normalize_summary_sentence(s, language) for s in split_sentences(block)]
        sentences = [s for s in sentences if s]
        if sentences:
            sentence_budget = 2 if language == "zh" else 1
            composed = " ".join(sentences[:sentence_budget])
            return clip(composed, 280)

    fallback_sentences = [normalize_summary_sentence(s, language) for s in split_sentences(cleaned)]
    fallback_sentences = [s for s in fallback_sentences if s]
    if fallback_sentences:
        fallback = " ".join(fallback_sentences[:1 if language == "pt" else 2])
        return clip(fallback, 220)

    return clip(case_type, 120) if case_type else ""


def sentence_holding_score(sentence: str, language: str) -> int:
    s = normalize_whitespace(sentence)
    lower = s.lower()
    score = 0

    if language == "zh":
        primary = ["裁定", "判決", "決定", "駁回", "不批准", "不予批准", "確認", "維持原審", "維持原判", "上訴理由不成立"]
        secondary = ["聲請", "上訴", "改判", "判處"]
    else:
        primary = [
            "negar provimento",
            "negou provimento",
            "julga-se improcedente",
            "julgar improcedente",
            "julgado improcedente",
            "julga improcedente",
            "manter a decisão",
            "acordam",
            "decisão",
            "condenar",
            "absolver",
        ]
        secondary = ["recurso", "sentença recorrida", "tribunal", "mantendo-se"]

    for token in primary:
        if token in lower:
            score += 4
    for token in secondary:
        if token in lower:
            score += 1

    if len(s) > 260:
        score -= 2
    if len(s) < 8:
        score -= 2

    return score


def extract_holding(language: str, text: str) -> str:
    cleaned = normalize_whitespace(text)
    if not cleaned:
        return ""

    sentences = split_sentences(cleaned)
    if not sentences:
        return ""

    tail_start = max(0, len(sentences) // 2)
    candidate_pool = sentences[tail_start:] if len(sentences) > 4 else sentences
    scored = [
        (sentence_holding_score(sentence, language), idx, sentence)
        for idx, sentence in enumerate(candidate_pool, start=tail_start)
    ]
    viable = [item for item in scored if item[0] > 0]
    if viable:
        # Prefer high score, then later sentence index to bias towards operative disposition.
        viable.sort(key=lambda item: (item[0], -len(item[2]), item[1]), reverse=True)
        return clip(normalize_summary_sentence(viable[0][2], language), 220)

    tail = sentences[-2:] if len(sentences) >= 2 else sentences
    return clip(normalize_summary_sentence(" ".join(tail), language), 220)


def extract_legal_basis(language: str, text: str) -> list[str]:
    cleaned = normalize_whitespace(text)
    if not cleaned:
        return []

    if language == "zh":
        raw_matches = re.findall(r"第\s*\d+\s*(?:之\s*\d+)?\s*條", cleaned)
        normalized = [re.sub(r"\s+", "", item) for item in raw_matches]
    else:
        raw_matches = re.findall(r"art(?:igo|\.)?\s*\d+[.º°o]*", cleaned, flags=re.IGNORECASE)
        normalized = [re.sub(r"\s+", " ", item).strip().lower() for item in raw_matches]

    uniq: list[str] = []
    seen: set[str] = set()
    for item in normalized:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        uniq.append(item)
        if len(uniq) >= 8:
            break
    return uniq


def extract_disputed_issues(language: str, text: str, case_type: str) -> list[str]:
    cleaned = normalize_whitespace(text)
    if not cleaned:
        return [case_type] if case_type else []

    if language == "zh":
        patterns = [r"主要問題\s*[:：]\s*([^。]+)", r"爭議焦點\s*[:：]\s*([^。]+)"]
    else:
        patterns = [r"Assunto\s*[:：]\s*([^\.]+)", r"Quest[õo]es\s*[:：]\s*([^\.]+)"]

    for pattern in patterns:
        match = re.search(pattern, cleaned, flags=re.IGNORECASE)
        if not match:
            continue
        issues = split_issue_candidates(match.group(1))
        if issues:
            return issues[:8]

    return [case_type] if case_type else []


def build_case_metadata(case_chunks: list[CaseChunk]) -> dict[str, Any]:
    head = case_chunks[0]
    combined_text = "\n".join(chunk.chunk_text for chunk in case_chunks)

    summary = extract_case_summary(head.language, combined_text, head.case_type)
    holding = extract_holding(head.language, combined_text)
    legal_basis = extract_legal_basis(head.language, combined_text)
    disputed_issues = extract_disputed_issues(head.language, combined_text, head.case_type)

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
                {
                    path
                    for path in [head.source_metadata_path, head.source_full_text_path]
                    if path
                }
            ),
        },
        "generated_digest_metadata": {
            "case_summary": summary,
            "holding": holding,
            "legal_basis": legal_basis,
            "disputed_issues": disputed_issues,
        },
        "generation_status": "deterministic_improved_day41",
        "generation_method": "deterministic_rule_based_extraction_local_only",
        "provenance_notes": [
            "No LLM used.",
            "No external API/database used.",
            "Day 41 targeted rule refinement (case_summary/holding priority).",
        ],
    }


def is_populated(value: Any) -> bool:
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, list):
        return len(value) > 0
    return value is not None


def compute_field_population_stats(items: list[dict[str, Any]]) -> dict[str, int]:
    fields = ["case_summary", "holding", "legal_basis", "disputed_issues"]
    stats = {"cases_processed": len(items)}
    for field in fields:
        stats[f"{field}_populated"] = sum(
            1
            for item in items
            if is_populated(item.get("generated_digest_metadata", {}).get(field))
        )
    return stats


def write_jsonl(path: Path, items: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_obj:
        for item in items:
            file_obj.write(json.dumps(item, ensure_ascii=False) + "\n")


def build_report_lines(
    *,
    input_path: Path,
    output_path: Path,
    stats: dict[str, int],
    sample_items: list[dict[str, Any]],
) -> list[str]:
    success = (
        stats["cases_processed"] > 0
        and stats["case_summary_populated"] > 0
        and stats["holding_populated"] > 0
        and stats["legal_basis_populated"] > 0
        and stats["disputed_issues_populated"] > 0
    )

    lines = [
        "Deterministic Metadata Extraction Improved Rules Report - Day 41",
        f"input_chunks_path: {input_path}",
        f"output_jsonl_path: {output_path}",
        f"cases processed: {stats['cases_processed']}",
        f"case_summary populated: {stats['case_summary_populated']}",
        f"holding populated: {stats['holding_populated']}",
        f"legal_basis populated: {stats['legal_basis_populated']}",
        f"disputed_issues populated: {stats['disputed_issues_populated']}",
        f"whether deterministic metadata extraction rule improvement appears successful: {success}",
        "",
        "Rule changes:",
        "- Prefer heading-level concise issue extraction for case_summary (zh: 主題/主要問題, pt: Assunto/Descritores).",
        "- Tighter heading stop-boundary handling to avoid summary bleed into procedural sections.",
        "- Holding uses scored dispositive sentence selection with zh/pt-specific keywords.",
        "- Disputed issues kept conservative to avoid regressions (pattern-first + case_type fallback).",
        "",
        "Sample shaped metadata outputs:",
    ]

    for idx, item in enumerate(sample_items, start=1):
        lines.append(f"\n=== sample_case_{idx} ===")
        lines.append(json.dumps(item, ensure_ascii=False, indent=2))

    return lines


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Improve deterministic metadata extraction rules (Day 41).")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT_PATH, help="Input bm25 chunks jsonl path")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH, help="Per-case shaped metadata output jsonl path")
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT_PATH, help="Output report txt path")
    parser.add_argument(
        "--sample-cases-in-report",
        type=int,
        default=DEFAULT_SAMPLE_CASES_IN_REPORT,
        help="How many sample cases to include in report",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if not args.input.exists():
        raise FileNotFoundError(f"Input chunks file not found: {args.input}")

    chunks = load_chunks(args.input)
    grouped = group_chunks_by_case(chunks)

    all_items: list[dict[str, Any]] = []
    for case_number in sorted(grouped.keys()):
        all_items.append(build_case_metadata(grouped[case_number]))

    write_jsonl(args.output, all_items)

    stats = compute_field_population_stats(all_items)
    sample_items = all_items[: max(args.sample_cases_in_report, 0)]
    report_lines = build_report_lines(
        input_path=args.input,
        output_path=args.output,
        stats=stats,
        sample_items=sample_items,
    )

    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    success = (
        stats["cases_processed"] > 0
        and stats["case_summary_populated"] > 0
        and stats["holding_populated"] > 0
        and stats["legal_basis_populated"] > 0
        and stats["disputed_issues_populated"] > 0
    )

    print(f"cases processed: {stats['cases_processed']}")
    print(f"case_summary populated: {stats['case_summary_populated']}")
    print(f"holding populated: {stats['holding_populated']}")
    print(f"legal_basis populated: {stats['legal_basis_populated']}")
    print(f"disputed_issues populated: {stats['disputed_issues_populated']}")
    print(f"whether deterministic metadata extraction rule improvement appears successful: {success}")
    print(f"output written: {args.output}")
    print(f"report written: {args.report}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
