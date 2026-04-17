#!/usr/bin/env python3
"""Portuguese / mixed-language legal query normalization and signal detection.

Deterministic and local-only:
- no external API
- no database
- no vector retrieval
"""

from __future__ import annotations

import re
import unicodedata

from crawler.retrieval.legal_lexical_mappings import VARIANT_TO_CANONICAL
from dataclasses import dataclass

CASE_NUMBER_PATTERN = re.compile(r"\b\d{1,6}\s*/\s*\d{4}(?:\s*/\s*[a-zA-Z]{1,3})?\b")
PT_WORD_PATTERN = re.compile(r"[a-zà-öø-ÿ]+", re.IGNORECASE)

PT_LEGAL_LEXICON = {
    "acórdão",
    "acordao",
    "tribunal",
    "processo",
    "decisão",
    "decisao",
    "recurso",
    "arguido",
    "autor",
    "réu",
    "reu",
    "juiz",
    "liberdade condicional",
    "erro ostensivo",
    "legis artis",
    "matéria cível",
    "materia civel",
    "responsabilidade civil",
    "dano moral",
    "habeas corpus",
    "suspensão da execução da pena",
    "suspensao da execucao da pena",
    "pena suspensa",
    "liberdade condicional",
    "difamação",
    "difamacao",
    "indemnização",
    "indemnizacao",
}

PT_CASE_STYLE_HINTS = (
    "processo n",
    "processo nº",
    "recurso",
    "matéria cível",
    "materia civel",
)

MULTI_ISSUE_CONNECTORS = (" e ", " ou ", " bem como ", "以及", "及", "與", "和", ";", "；")


@dataclass(frozen=True)
class PortugueseMixedNormalizationResult:
    normalized_query: str
    pt_lexicon_hits: list[str]
    cjk_char_count: int
    latin_word_count: int
    has_case_number: bool
    has_pt_case_style: bool
    mixed_language: bool
    multi_issue_hint: bool

    @property
    def language_signal_summary(self) -> str:
        lexicon_text = ", ".join(self.pt_lexicon_hits[:6]) if self.pt_lexicon_hits else "none"
        return (
            f"pt_lexicon_hits={len(self.pt_lexicon_hits)}[{lexicon_text}]"
            f"; latin_words={self.latin_word_count}"
            f"; cjk_chars={self.cjk_char_count}"
            f"; case_number={self.has_case_number}"
            f"; pt_case_style={self.has_pt_case_style}"
            f"; mixed_language={self.mixed_language}"
            f"; multi_issue_hint={self.multi_issue_hint}"
        )


class PortugueseMixedQueryNormalizer:
    """Deterministic normalization + language signal extraction for pt/mixed queries."""

    def normalize_and_detect(self, raw_query: str) -> PortugueseMixedNormalizationResult:
        normalized = self._normalize_text(raw_query)
        lowered = normalized.lower()
        lowered = self._apply_cross_lingual_variant_mapping(lowered)

        pt_hits = [token for token in sorted(PT_LEGAL_LEXICON, key=len, reverse=True) if token in lowered]
        cjk_chars = sum(1 for char in normalized if "\u4e00" <= char <= "\u9fff")
        latin_words = PT_WORD_PATTERN.findall(lowered)
        latin_word_count = len(latin_words)
        has_case_number = bool(CASE_NUMBER_PATTERN.search(lowered))
        has_pt_case_style = any(hint in lowered for hint in PT_CASE_STYLE_HINTS)

        mixed_language = bool(cjk_chars >= 1 and latin_word_count >= 2)
        if not mixed_language and cjk_chars >= 2 and any(hit in lowered for hit in ("liberdade condicional", "recurso")):
            mixed_language = True

        multi_issue_hint = False
        lowered_padded = f" {lowered} "
        connector_hits = sum(1 for token in MULTI_ISSUE_CONNECTORS if token in lowered_padded)
        if connector_hits >= 2:
            multi_issue_hint = True

        return PortugueseMixedNormalizationResult(
            normalized_query=normalized,
            pt_lexicon_hits=pt_hits,
            cjk_char_count=cjk_chars,
            latin_word_count=latin_word_count,
            has_case_number=has_case_number,
            has_pt_case_style=has_pt_case_style,
            mixed_language=mixed_language,
            multi_issue_hint=multi_issue_hint,
        )

    def _normalize_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKC", text or "")
        normalized = normalized.strip()
        normalized = normalized.replace("（", "(").replace("）", ")")
        normalized = normalized.replace("　", " ")
        normalized = normalized.replace("n o", "nº")
        normalized = normalized.replace("n. o", "nº")
        normalized = normalized.replace("n º", "nº")
        normalized = re.sub(r"\bprocesso\s+n\s*[ºo]?\b", "processo nº", normalized, flags=re.IGNORECASE)
        normalized = re.sub(r"\s*/\s*", "/", normalized)
        normalized = re.sub(r"\s+", " ", normalized)
        return normalized.strip()

    @staticmethod
    def _apply_cross_lingual_variant_mapping(text: str) -> str:
        normalized = text
        for variant in sorted(VARIANT_TO_CANONICAL, key=len, reverse=True):
            canonical = VARIANT_TO_CANONICAL[variant].lower()
            if variant in normalized:
                normalized = normalized.replace(variant, canonical)
        return normalized
