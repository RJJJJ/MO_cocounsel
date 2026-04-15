#!/usr/bin/env python3
"""Chinese legal query normalization helpers for local BM25 retrieval."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass

CASE_NUMBER_PATTERN = re.compile(
    r"(?:第\s*)?(\d{1,5})\s*[/／]\s*(\d{2,4})(?:\s*[/／]\s*([A-Za-z]))?\s*(?:號)?",
    re.IGNORECASE,
)

PUNCT_TRANSLATION = str.maketrans(
    {
        "，": ",",
        "。": ".",
        "；": ";",
        "：": ":",
        "（": "(",
        "）": ")",
        "【": "[",
        "】": "]",
        "「": '"',
        "」": '"',
        "、": " ",
        "／": "/",
        "－": "-",
        "—": "-",
        "–": "-",
        "‧": ".",
    }
)

VARIANT_TO_CANONICAL = {
    "提前釋放": "假釋",
    "提前释放": "假釋",
    "保釋": "假釋",
    "量刑明顯過重": "量刑過重",
    "刑罰過重": "量刑過重",
    "判刑過重": "量刑過重",
    "合約不能履行": "合同不能履行",
    "合同之不能履行": "合同不能履行",
    "不能履行合同": "合同不能履行",
    "損失賠償": "損害賠償",
    "賠償損失": "損害賠償",
    "诽谤": "誹謗",
    "损害赔偿": "損害賠償",
}

HIGH_VALUE_EXPANSION = {
    "假釋": ["提前釋放", "刑法典第56條", "釋放被判刑者"],
    "量刑過重": ["量刑明顯過重", "刑罰過重", "改判"],
    "合同不能履行": ["合約不能履行", "履行不能", "債務不履行"],
    "損害賠償": ["賠償損失", "損失賠償", "民事賠償"],
    "誹謗": ["名譽", "侮辱", "侵犯名譽"],
    "違令": ["違反法庭命令", "不遵令", "拒不履行命令"],
}


@dataclass(frozen=True)
class NormalizedQuery:
    normalized_query: str
    expanded_query: str
    applied_rules: list[str]
    expansions_added: list[str]


class ChineseLegalQueryNormalizer:
    """Deterministic normalization layer focused on Chinese legal queries."""

    def normalize_query(self, query: str) -> NormalizedQuery:
        original = query or ""
        applied_rules: list[str] = []

        normalized = unicodedata.normalize("NFKC", original)
        if normalized != original:
            applied_rules.append("unicode_nfkc")

        punct_normalized = normalized.translate(PUNCT_TRANSLATION)
        if punct_normalized != normalized:
            applied_rules.append("punctuation_width_normalization")
        normalized = punct_normalized

        normalized = normalized.replace("第 ", "第")
        normalized = re.sub(r"\s+", " ", normalized).strip().lower()

        normalized, case_rule_applied = self._normalize_case_numbers(normalized)
        if case_rule_applied:
            applied_rules.append("case_number_format_normalization")

        normalized, variant_applied = self._normalize_legal_variants(normalized)
        if variant_applied:
            applied_rules.append("legal_variant_mapping")

        expansions = self._expand_high_value_terms(normalized)
        if expansions:
            applied_rules.append("high_value_legal_query_expansion")

        expanded_query = " ".join([normalized, *expansions]).strip()
        return NormalizedQuery(
            normalized_query=normalized,
            expanded_query=expanded_query,
            applied_rules=applied_rules,
            expansions_added=expansions,
        )

    def _normalize_case_numbers(self, text: str) -> tuple[str, bool]:
        changed = False

        def repl(match: re.Match[str]) -> str:
            nonlocal changed
            year = match.group(2)
            suffix = match.group(3)
            canonical = f"{int(match.group(1))}/{year}"
            if suffix:
                canonical = f"{canonical}/{suffix.lower()}"
            original = match.group(0)
            if original != canonical:
                changed = True
            return canonical

        normalized = CASE_NUMBER_PATTERN.sub(repl, text)
        normalized = re.sub(r"\s*/\s*", "/", normalized)
        normalized = re.sub(r"\s+", " ", normalized).strip()
        return normalized, changed

    def _normalize_legal_variants(self, text: str) -> tuple[str, bool]:
        changed = False
        normalized = text
        for variant in sorted(VARIANT_TO_CANONICAL, key=len, reverse=True):
            canonical = VARIANT_TO_CANONICAL[variant]
            if variant in normalized:
                normalized = normalized.replace(variant, canonical)
                changed = True
        return normalized, changed

    def _expand_high_value_terms(self, text: str) -> list[str]:
        expansions: list[str] = []
        for canonical, terms in HIGH_VALUE_EXPANSION.items():
            if canonical in text:
                for term in terms:
                    if term not in text and term not in expansions:
                        expansions.append(term)
        return expansions
