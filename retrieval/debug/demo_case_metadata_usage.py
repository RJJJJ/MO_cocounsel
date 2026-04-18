#!/usr/bin/env python3
"""Minimal demo: prove case_metadata_v1 can be consumed by case-level outputs."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

DEFAULT_ATTACHED_MANIFEST = Path("data/corpus/raw/macau_court_cases_full_metadata_v1/manifest.metadata_attached_v1.jsonl")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Demo usage of case_metadata_v1 fields")
    parser.add_argument("--attached-manifest", type=Path, default=DEFAULT_ATTACHED_MANIFEST)
    parser.add_argument("--holding-case", default="")
    parser.add_argument("--issue-query", default="上訴是否具理由")
    parser.add_argument("--legal-basis-query", default="第40條")
    parser.add_argument("--top-k", type=int, default=3)
    return parser.parse_args()


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def load_rows(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as fh:
        for line in fh:
            raw = line.strip()
            if not raw:
                continue
            payload = json.loads(raw)
            if isinstance(payload, dict):
                rows.append(payload)
    return rows


def tokenize(text: str) -> list[str]:
    text = normalize_space(text).lower()
    if not text:
        return []
    zh_chunks = re.findall(r"[\u4e00-\u9fff]{2,}", text)
    latin_chunks = re.findall(r"[a-z0-9_./-]+", text)
    return zh_chunks + latin_chunks


def score_overlap(query: str, targets: list[str]) -> float:
    q = set(tokenize(query))
    if not q:
        return 0.0
    t = set(tokenize(" ".join(targets)))
    if not t:
        return 0.0
    return len(q & t) / len(q)


def find_holding_demo(rows: list[dict[str, Any]], case_number: str) -> dict[str, Any] | None:
    if case_number:
        for row in rows:
            if normalize_space(row.get("authoritative_case_number")) == normalize_space(case_number):
                return row
    for row in rows:
        holding = normalize_space((row.get("case_metadata_v1") or {}).get("holding"))
        if holding:
            return row
    return None


def top_issue_matches(rows: list[dict[str, Any]], query: str, top_k: int) -> list[dict[str, Any]]:
    ranked: list[tuple[float, dict[str, Any]]] = []
    for row in rows:
        issues = (row.get("case_metadata_v1") or {}).get("disputed_issues") or []
        score = score_overlap(query, issues)
        if score > 0:
            ranked.append((score, row))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [{"score": s, "row": r} for s, r in ranked[:top_k]]


def top_legal_basis_matches(rows: list[dict[str, Any]], query: str, top_k: int) -> list[dict[str, Any]]:
    ranked: list[tuple[float, dict[str, Any]]] = []
    for row in rows:
        bases = (row.get("case_metadata_v1") or {}).get("legal_basis") or []
        score = score_overlap(query, bases)
        if score > 0:
            ranked.append((score, row))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [{"score": s, "row": r} for s, r in ranked[:top_k]]


def main() -> None:
    args = parse_args()
    rows = load_rows(args.attached_manifest)

    holding_row = find_holding_demo(rows, args.holding_case)
    issue_rows = top_issue_matches(rows, args.issue_query, args.top_k)
    basis_rows = top_legal_basis_matches(rows, args.legal_basis_query, args.top_k)

    print("=== Demo A: 用 holding 回答『法院怎麼判』 ===")
    if holding_row:
        md = holding_row.get("case_metadata_v1") or {}
        print(f"case={holding_row.get('authoritative_case_number')} sentence_id={holding_row.get('sentence_id')}")
        print("Q: 法院怎麼判？")
        print(f"A: {normalize_space(md.get('holding')) or '[無 holding]'}")
    else:
        print("找不到可用 holding。")

    print("\n=== Demo B: disputed_issues query-to-issue matching ===")
    print(f"query={args.issue_query}")
    if not issue_rows:
        print("無可匹配結果。")
    for idx, item in enumerate(issue_rows, start=1):
        row = item["row"]
        md = row.get("case_metadata_v1") or {}
        print(
            f"[{idx}] score={item['score']:.3f} case={row.get('authoritative_case_number')} "
            f"issues={md.get('disputed_issues') or []}"
        )

    print("\n=== Demo C: legal_basis 法律依據召回 ===")
    print(f"query={args.legal_basis_query}")
    if not basis_rows:
        print("無可匹配結果。")
    for idx, item in enumerate(basis_rows, start=1):
        row = item["row"]
        md = row.get("case_metadata_v1") or {}
        print(
            f"[{idx}] score={item['score']:.3f} case={row.get('authoritative_case_number')} "
            f"legal_basis={md.get('legal_basis') or []}"
        )


if __name__ == "__main__":
    main()
