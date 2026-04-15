#!/usr/bin/env python3
"""Day 35 - deterministic exact case-number-heavy retrieval path (local only).

Scope constraints:
- local-only
- no database
- no external API
- no vector retrieval
"""

from __future__ import annotations

import argparse
import json
import math
import re
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

PREPARED_ROOT = Path("data/corpus/prepared/macau_court_cases")
BM25_CHUNKS_PATH = PREPARED_ROOT / "bm25_chunks.jsonl"
DEMO_REPORT_PATH = Path("data/eval/exact_case_number_lookup_demo_report.txt")

CASE_NUMBER_REGEX = re.compile(
    r"(?:第\s*)?(\d{1,6})\s*/\s*(\d{4})(?:\s*/\s*([a-zA-Z]{1,3}))?(?:\s*號)?",
    re.IGNORECASE,
)
LATIN_OR_NUMERIC = re.compile(r"[a-z0-9]+", re.IGNORECASE)
CJK_SEQUENCE = re.compile(r"[\u4e00-\u9fff]+")


@dataclass(frozen=True)
class CaseNumberNormalizationResult:
    raw_query: str
    normalized_case_query: str | None
    extracted_components: tuple[str, str, str | None] | None


@dataclass(frozen=True)
class RetrievalHit:
    chunk_id: str
    authoritative_case_number: str
    authoritative_decision_date: str
    court: str
    language: str
    case_type: str
    pdf_url: str
    text_url_or_action: str
    score: float
    retrieval_source: str


@dataclass(frozen=True)
class ExactCaseLookupResult:
    raw_query: str
    normalized_case_query: str | None
    exact_match_candidates_found: int
    fallback_used: bool
    top_k_returned: int
    exact_case_number_lookup_refinement_successful: bool
    hits: list[RetrievalHit]


class ExactCaseNumberNormalizer:
    @staticmethod
    def _to_nfkc(text: str) -> str:
        return unicodedata.normalize("NFKC", text or "")

    def normalize_case_query(self, raw_query: str) -> CaseNumberNormalizationResult:
        normalized_text = self._to_nfkc(raw_query).strip()
        match = CASE_NUMBER_REGEX.search(normalized_text)
        if not match:
            return CaseNumberNormalizationResult(
                raw_query=raw_query,
                normalized_case_query=None,
                extracted_components=None,
            )

        number, year, suffix = match.group(1), match.group(2), match.group(3)
        number = str(int(number))
        year = str(int(year)).zfill(4)
        suffix = suffix.upper() if suffix else None

        canonical = f"{number}/{year}"
        if suffix:
            canonical = f"{canonical}/{suffix}"

        return CaseNumberNormalizationResult(
            raw_query=raw_query,
            normalized_case_query=canonical,
            extracted_components=(number, year, suffix),
        )

    def normalize_case_id_for_match(self, case_id: str) -> str | None:
        parsed = self.normalize_case_query(case_id)
        return parsed.normalized_case_query


class LightweightBM25:
    def __init__(self, records: list[dict[str, Any]], k1: float = 1.5, b: float = 0.75) -> None:
        self.records = records
        self.k1 = k1
        self.b = b
        self.doc_term_freqs: list[Counter[str]] = []
        self.doc_lengths: list[int] = []
        self.doc_freqs: Counter[str] = Counter()
        self.avg_doc_len: float = 0.0
        self._build()

    def _tokenize(self, text: str) -> list[str]:
        normalized = unicodedata.normalize("NFKC", text or "").lower()
        tokens: list[str] = LATIN_OR_NUMERIC.findall(normalized)
        for seq in CJK_SEQUENCE.findall(normalized):
            if len(seq) == 1:
                tokens.append(seq)
            else:
                tokens.extend(seq[i : i + 2] for i in range(len(seq) - 1))
        return [tok for tok in tokens if tok]

    def _build(self) -> None:
        for rec in self.records:
            text = " ".join(
                [
                    str(rec.get("authoritative_case_number", "")),
                    str(rec.get("bm25_text", "")),
                    str(rec.get("chunk_text", "")),
                ]
            )
            tokens = self._tokenize(text)
            tf = Counter(tokens)
            self.doc_term_freqs.append(tf)
            self.doc_lengths.append(len(tokens))
            for term in tf:
                self.doc_freqs[term] += 1

        if self.doc_lengths:
            self.avg_doc_len = sum(self.doc_lengths) / len(self.doc_lengths)

    def _idf(self, term: str) -> float:
        n = len(self.records)
        df = self.doc_freqs.get(term, 0)
        return math.log(1 + (n - df + 0.5) / (df + 0.5))

    def search(self, query: str, top_k: int) -> list[tuple[int, float]]:
        q_tokens = self._tokenize(query)
        if not q_tokens:
            return []

        scored: list[tuple[int, float]] = []
        for idx, tf in enumerate(self.doc_term_freqs):
            doc_len = self.doc_lengths[idx]
            score = 0.0
            for term in q_tokens:
                f = tf.get(term, 0)
                if f == 0:
                    continue
                idf = self._idf(term)
                numerator = f * (self.k1 + 1)
                denominator = f + self.k1 * (1 - self.b + self.b * doc_len / max(self.avg_doc_len, 1.0))
                score += idf * (numerator / denominator)
            if score > 0:
                scored.append((idx, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


class ExactCaseNumberRetriever:
    def __init__(self, records: list[dict[str, Any]], min_exact_hits_before_no_fallback: int = 3) -> None:
        self.records = records
        self.normalizer = ExactCaseNumberNormalizer()
        self.bm25 = LightweightBM25(records)
        self.min_exact_hits_before_no_fallback = min_exact_hits_before_no_fallback
        self.case_to_indices: dict[str, list[int]] = {}
        self._build_case_index()

    def _build_case_index(self) -> None:
        for idx, rec in enumerate(self.records):
            authoritative_case_number = str(rec.get("authoritative_case_number", "")).strip()
            normalized = self.normalizer.normalize_case_id_for_match(authoritative_case_number)
            if not normalized:
                continue
            self.case_to_indices.setdefault(normalized, []).append(idx)

    @staticmethod
    def _to_hit(record: dict[str, Any], score: float, retrieval_source: str) -> RetrievalHit:
        return RetrievalHit(
            chunk_id=str(record.get("chunk_id", "")),
            authoritative_case_number=str(record.get("authoritative_case_number", "")),
            authoritative_decision_date=str(record.get("authoritative_decision_date", "")),
            court=str(record.get("court", "")),
            language=str(record.get("language", "")),
            case_type=str(record.get("case_type", "")),
            pdf_url=str(record.get("pdf_url", "")),
            text_url_or_action=str(record.get("text_url_or_action", "")),
            score=round(score, 4),
            retrieval_source=retrieval_source,
        )

    def retrieve(self, raw_query: str, top_k: int = 8) -> ExactCaseLookupResult:
        norm = self.normalizer.normalize_case_query(raw_query)

        exact_hits: list[RetrievalHit] = []
        used_indices: set[int] = set()
        if norm.normalized_case_query:
            for idx in self.case_to_indices.get(norm.normalized_case_query, []):
                used_indices.add(idx)
                exact_hits.append(
                    self._to_hit(
                        self.records[idx],
                        score=100.0,
                        retrieval_source=f"exact_case_number_match:{norm.normalized_case_query}",
                    )
                )

        fallback_used = False
        if len(exact_hits) < self.min_exact_hits_before_no_fallback:
            fallback_used = True
            bm25_candidates = self.bm25.search(raw_query, top_k=max(top_k * 2, 10))
            for idx, bm25_score in bm25_candidates:
                if idx in used_indices:
                    continue
                used_indices.add(idx)
                exact_hits.append(
                    self._to_hit(
                        self.records[idx],
                        score=min(9.9, bm25_score),
                        retrieval_source="bm25_fallback",
                    )
                )
                if len(exact_hits) >= top_k:
                    break

        exact_hits.sort(key=lambda hit: hit.score, reverse=True)
        final_hits = exact_hits[:top_k]

        successful = bool(norm.normalized_case_query) and any(
            hit.retrieval_source.startswith("exact_case_number_match") for hit in final_hits
        )

        return ExactCaseLookupResult(
            raw_query=raw_query,
            normalized_case_query=norm.normalized_case_query,
            exact_match_candidates_found=len(self.case_to_indices.get(norm.normalized_case_query or "", [])),
            fallback_used=fallback_used,
            top_k_returned=len(final_hits),
            exact_case_number_lookup_refinement_successful=successful,
            hits=final_hits,
        )


def load_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"Prepared corpus not found: {path}")

    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            records.append(json.loads(line))

    if not records:
        raise RuntimeError("No records loaded from local prepared corpus")

    return records


def render_terminal_summary(result: ExactCaseLookupResult) -> str:
    lines = [
        f"raw query: {result.raw_query}",
        f"normalized case query: {result.normalized_case_query or '[none]'}",
        f"exact match candidates found: {result.exact_match_candidates_found}",
        f"fallback used: {'yes' if result.fallback_used else 'no'}",
        f"top_k returned: {result.top_k_returned}",
        (
            "whether exact case-number lookup refinement appears successful: "
            f"{'yes' if result.exact_case_number_lookup_refinement_successful else 'no'}"
        ),
        "",
        "top hits:",
    ]

    for idx, hit in enumerate(result.hits, start=1):
        lines.append(
            f"{idx}. {hit.chunk_id} | {hit.authoritative_case_number} | {hit.authoritative_decision_date} "
            f"| score={hit.score} | source={hit.retrieval_source}"
        )

    return "\n".join(lines)


def write_demo_report(result: ExactCaseLookupResult, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "summary": {
            "raw_query": result.raw_query,
            "normalized_case_query": result.normalized_case_query,
            "exact_match_candidates_found": result.exact_match_candidates_found,
            "fallback_used": result.fallback_used,
            "top_k_returned": result.top_k_returned,
            "exact_case_number_lookup_refinement_successful": result.exact_case_number_lookup_refinement_successful,
        },
        "hits": [asdict(hit) for hit in result.hits],
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Deterministic exact case-number-heavy retrieval path")
    parser.add_argument("--query", required=True, help="Raw legal research query")
    parser.add_argument("--top-k", type=int, default=8, help="Number of hits to return")
    parser.add_argument(
        "--corpus-path",
        type=Path,
        default=BM25_CHUNKS_PATH,
        help="Local prepared corpus path (JSONL)",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=DEMO_REPORT_PATH,
        help="Where to write local demo report",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records = load_records(args.corpus_path)
    retriever = ExactCaseNumberRetriever(records=records)
    result = retriever.retrieve(raw_query=args.query, top_k=args.top_k)

    summary = render_terminal_summary(result)
    print(summary)
    write_demo_report(result, args.report_path)


if __name__ == "__main__":
    main()
