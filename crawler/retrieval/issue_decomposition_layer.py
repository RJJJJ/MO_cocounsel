#!/usr/bin/env python3
"""Deterministic local issue decomposition layer for legal retrieval pre-processing.

Day 30 scope:
- local-only decomposition
- no database integration
- no external API calls
- no LLM integration
- no changes to existing retrieval main flow

Transforms a raw legal query into structured retrieval-oriented components that
can be consumed by future retrieval orchestration.
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

DEMO_REPORT_PATH = Path("data/eval/issue_decomposition_demo_report.txt")

CASE_NUMBER_PATTERN = re.compile(r"\b\d{1,5}/\d{4}\b")

LEGAL_TERM_CANONICAL_MAP: dict[str, str] = {
    "假釋": "假釋",
    "假释": "假釋",
    "量刑過重": "量刑過重",
    "量刑过重": "量刑過重",
    "誹謗": "誹謗",
    "诽谤": "誹謗",
    "緩刑": "緩刑",
    "缓刑": "緩刑",
    "詐騙": "詐騙",
    "诈骗": "詐騙",
    "加重詐騙": "加重詐騙",
    "加重诈骗": "加重詐騙",
    "損害賠償": "損害賠償",
    "损害赔偿": "損害賠償",
    "過失": "過失",
    "故意": "故意",
    "自首": "自首",
}

PROCEDURE_TERM_CANONICAL_MAP: dict[str, str] = {
    "上訴": "上訴",
    "上诉": "上訴",
    "撤銷": "撤銷",
    "撤销": "撤銷",
    "駁回": "駁回",
    "驳回": "駁回",
    "改判": "改判",
    "抗告": "抗告",
    "再審": "再審",
    "再审": "再審",
}

FACT_TERMS = (
    "被告",
    "原告",
    "告訴人",
    "證據",
    "證人",
    "供述",
    "契約",
    "合同",
    "侵占",
    "侵權",
    "賠償",
    "損失",
    "傷害",
)

CONNECTOR_PATTERN = re.compile(r"[，,、;；]+|\s+|\b(?:與|和|及|或|並|且|還有)\b")


@dataclass(frozen=True)
class IssueDecompositionResult:
    original_query: str
    normalized_query: str
    main_issue: str
    sub_issues: list[str]
    query_terms: list[str]
    retrieval_subqueries: list[str]


class RuleBasedIssueDecomposer:
    """Rule-based Chinese legal issue decomposition for retrieval pre-processing."""

    def normalize_query(self, raw_query: str) -> str:
        normalized = raw_query.strip()
        normalized = normalized.replace("（", "(").replace("）", ")")
        normalized = normalized.replace("　", " ")
        normalized = re.sub(r"\s+", " ", normalized)
        normalized = re.sub(r"[，,、;；]+", " ", normalized)
        return normalized.strip()

    def decompose(self, raw_query: str) -> IssueDecompositionResult:
        normalized_query = self.normalize_query(raw_query)
        case_numbers = self._extract_case_numbers(normalized_query)

        canonical_legal_terms = self._extract_canonical_terms(normalized_query, LEGAL_TERM_CANONICAL_MAP)
        canonical_procedure_terms = self._extract_canonical_terms(normalized_query, PROCEDURE_TERM_CANONICAL_MAP)
        fact_terms = self._extract_fact_terms(normalized_query)

        main_issue = self._choose_main_issue(
            normalized_query=normalized_query,
            case_numbers=case_numbers,
            legal_terms=canonical_legal_terms,
            procedure_terms=canonical_procedure_terms,
            fact_terms=fact_terms,
        )

        sub_issues = self._build_sub_issues(
            main_issue=main_issue,
            case_numbers=case_numbers,
            legal_terms=canonical_legal_terms,
            procedure_terms=canonical_procedure_terms,
            fact_terms=fact_terms,
        )

        query_terms = self._build_query_terms(
            case_numbers=case_numbers,
            legal_terms=canonical_legal_terms,
            procedure_terms=canonical_procedure_terms,
            fact_terms=fact_terms,
        )

        retrieval_subqueries = self._build_retrieval_subqueries(
            original_query=raw_query,
            normalized_query=normalized_query,
            main_issue=main_issue,
            case_numbers=case_numbers,
            legal_terms=canonical_legal_terms,
            procedure_terms=canonical_procedure_terms,
            fact_terms=fact_terms,
            sub_issues=sub_issues,
        )

        return IssueDecompositionResult(
            original_query=raw_query,
            normalized_query=normalized_query,
            main_issue=main_issue,
            sub_issues=sub_issues,
            query_terms=query_terms,
            retrieval_subqueries=retrieval_subqueries,
        )

    def _extract_case_numbers(self, query: str) -> list[str]:
        return self._unique_in_order(CASE_NUMBER_PATTERN.findall(query))

    def _extract_canonical_terms(self, query: str, canonical_map: dict[str, str]) -> list[str]:
        found: list[str] = []
        for term, canonical in canonical_map.items():
            if term in query:
                found.append(canonical)
        return self._unique_in_order(found)

    def _extract_fact_terms(self, query: str) -> list[str]:
        found = [term for term in FACT_TERMS if term in query]

        segments = [segment.strip() for segment in CONNECTOR_PATTERN.split(query) if segment.strip()]
        for segment in segments:
            if segment in LEGAL_TERM_CANONICAL_MAP:
                continue
            if segment in PROCEDURE_TERM_CANONICAL_MAP:
                continue
            if CASE_NUMBER_PATTERN.fullmatch(segment):
                continue
            if 2 <= len(segment) <= 12 and all(char not in "()[]{}" for char in segment):
                if any(term in segment for term in FACT_TERMS):
                    found.append(segment)

        return self._unique_in_order(found)

    def _choose_main_issue(
        self,
        normalized_query: str,
        case_numbers: list[str],
        legal_terms: list[str],
        procedure_terms: list[str],
        fact_terms: list[str],
    ) -> str:
        if legal_terms:
            return legal_terms[0]
        if procedure_terms:
            return procedure_terms[0]
        if case_numbers and len(normalized_query) <= 24:
            return f"案件編號 {case_numbers[0]}"
        if fact_terms:
            return fact_terms[0]
        return normalized_query

    def _build_sub_issues(
        self,
        main_issue: str,
        case_numbers: list[str],
        legal_terms: list[str],
        procedure_terms: list[str],
        fact_terms: list[str],
    ) -> list[str]:
        candidates: list[str] = []
        candidates.extend(legal_terms)
        candidates.extend(procedure_terms)
        candidates.extend(f"案件編號 {number}" for number in case_numbers)
        candidates.extend(fact_terms)

        deduped = [item for item in self._unique_in_order(candidates) if item != main_issue]
        return deduped[:6]

    def _build_query_terms(
        self,
        case_numbers: list[str],
        legal_terms: list[str],
        procedure_terms: list[str],
        fact_terms: list[str],
    ) -> list[str]:
        combined = case_numbers + legal_terms + procedure_terms + fact_terms
        return self._unique_in_order(combined)[:10]

    def _build_retrieval_subqueries(
        self,
        original_query: str,
        normalized_query: str,
        main_issue: str,
        case_numbers: list[str],
        legal_terms: list[str],
        procedure_terms: list[str],
        fact_terms: list[str],
        sub_issues: list[str],
    ) -> list[str]:
        candidates: list[str] = [original_query.strip()]

        if normalized_query and normalized_query != original_query.strip():
            candidates.append(normalized_query)

        if main_issue:
            candidates.append(main_issue)

        canonical_terms = self._unique_in_order(legal_terms + procedure_terms)
        if canonical_terms:
            candidates.append(" ".join(canonical_terms[:4]))

        if case_numbers and canonical_terms:
            candidates.append(f"{case_numbers[0]} {' '.join(canonical_terms[:2])}")
        elif case_numbers:
            candidates.append(f"案件編號 {case_numbers[0]}")

        if legal_terms and fact_terms:
            candidates.append(f"{legal_terms[0]} {fact_terms[0]}")

        for sub_issue in sub_issues[:3]:
            candidates.append(sub_issue)

        cleaned = [item.strip() for item in candidates if item and item.strip()]
        return self._unique_in_order(cleaned)[:8]

    @staticmethod
    def _unique_in_order(items: list[str]) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for item in items:
            if item in seen:
                continue
            seen.add(item)
            result.append(item)
        return result


def decomposition_appears_successful(result: IssueDecompositionResult) -> bool:
    has_core = bool(result.main_issue.strip())
    has_subquery = bool(result.retrieval_subqueries)
    return has_core and has_subquery


def write_demo_report(result: IssueDecompositionResult, output_path: Path) -> None:
    is_successful = decomposition_appears_successful(result)

    lines = [
        "Issue Decomposition Layer Demo Report - Macau Court Cases",
        f"query_received: {result.original_query}",
        f"normalized_query: {result.normalized_query}",
        f"main_issue: {result.main_issue}",
        f"sub_issue_count: {len(result.sub_issues)}",
        f"retrieval_subquery_count: {len(result.retrieval_subqueries)}",
        f"issue_decomposition_appears_successful: {is_successful}",
        "query_terms:",
    ]

    for idx, term in enumerate(result.query_terms, start=1):
        lines.append(f"  [{idx}] {term}")

    lines.append("sub_issues:")
    for idx, issue in enumerate(result.sub_issues, start=1):
        lines.append(f"  [{idx}] {issue}")

    lines.append("retrieval_subqueries:")
    for idx, subquery in enumerate(result.retrieval_subqueries, start=1):
        lines.append(f"  [{idx}] {subquery}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local issue decomposition layer demo runner")
    parser.add_argument("query", type=str, help="raw legal query")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEMO_REPORT_PATH,
        help="path to local issue decomposition demo report",
    )
    parser.add_argument("--json", action="store_true", help="print decomposition result as JSON")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    decomposer = RuleBasedIssueDecomposer()
    result = decomposer.decompose(args.query)
    write_demo_report(result=result, output_path=args.output)

    success = decomposition_appears_successful(result)
    print(f"query received: {result.original_query}")
    print(f"normalized query: {result.normalized_query}")
    print(f"main issue: {result.main_issue}")
    print(f"sub issue count: {len(result.sub_issues)}")
    print(f"retrieval subquery count: {len(result.retrieval_subqueries)}")
    print(f"issue decomposition appears successful: {success}")

    if args.json:
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
