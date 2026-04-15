#!/usr/bin/env python3
"""Local BM25 query prototype for Macau court corpus (zh/pt aware)."""

from __future__ import annotations

import argparse
import json
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

PREPARED_ROOT = Path("data/corpus/prepared/macau_court_cases")
BM25_CHUNKS_PATH = PREPARED_ROOT / "bm25_chunks.jsonl"
DEMO_REPORT_PATH = PREPARED_ROOT / "bm25_query_demo_report.txt"

LATIN_TOKEN_PATTERN = re.compile(r"[a-zà-öø-ÿ]+(?:[-'][a-zà-öø-ÿ]+)*", re.IGNORECASE)
ALNUM_REF_PATTERN = re.compile(r"[a-z0-9]+(?:[./_-][a-z0-9]+)+", re.IGNORECASE)
CASE_NUMBER_PATTERN = re.compile(r"\b(?:proc\.?\s*)?[a-z]{0,6}\s*\d{1,5}\s*/\s*\d{2,4}\b", re.IGNORECASE)
CJK_CHAR_PATTERN = re.compile(r"[\u4e00-\u9fff]")
CJK_SEQUENCE_PATTERN = re.compile(r"[\u4e00-\u9fff]+")


@dataclass(frozen=True)
class TokenizerResult:
    tokens: list[str]
    strategy_name: str


@dataclass(frozen=True)
class RankedHit:
    score: float
    chunk_id: str
    authoritative_case_number: str
    authoritative_decision_date: str
    court: str
    language: str
    case_type: str
    chunk_text_preview: str
    pdf_url: str
    text_url_or_action: str


class MixedTokenizer:
    """Deterministic local tokenizer for mixed zh/pt legal text."""

    def __init__(self, mode: str = "deterministic") -> None:
        self.mode = mode
        self._jieba = None

        if mode in {"auto", "jieba"}:
            try:
                import jieba  # type: ignore

                self._jieba = jieba
            except Exception:
                if mode == "jieba":
                    raise RuntimeError("jieba mode selected but jieba is not installed")

    @staticmethod
    def normalize(text: str) -> str:
        normalized = unicodedata.normalize("NFKC", text or "")
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
        return normalized.lower().strip()

    @staticmethod
    def _normalize_case_reference(case_ref: str) -> str:
        collapsed = re.sub(r"\s+", "", case_ref.lower())
        return collapsed.replace("proc.", "proc").replace("proc", "proc")

    def _deterministic_tokens(self, text: str) -> list[str]:
        normalized = self.normalize(text)
        if not normalized:
            return []

        tokens: list[str] = []

        for case_ref in CASE_NUMBER_PATTERN.findall(normalized):
            tokens.append(self._normalize_case_reference(case_ref))

        for ref_token in ALNUM_REF_PATTERN.findall(normalized):
            tokens.append(ref_token)

        for latin in LATIN_TOKEN_PATTERN.findall(normalized):
            tokens.append(latin)

        for cjk_seq in CJK_SEQUENCE_PATTERN.findall(normalized):
            if len(cjk_seq) == 1:
                tokens.append(cjk_seq)
                continue
            for idx in range(len(cjk_seq) - 1):
                tokens.append(cjk_seq[idx : idx + 2])

        return [token for token in tokens if token]

    def tokenize(self, text: str) -> TokenizerResult:
        det_tokens = self._deterministic_tokens(text)

        if self.mode == "deterministic" or self._jieba is None:
            return TokenizerResult(tokens=det_tokens, strategy_name="deterministic_regex_plus_cjk_bigrams")

        normalized = self.normalize(text)
        jieba_tokens = [tok.strip() for tok in self._jieba.cut(normalized) if tok.strip()]

        merged: list[str] = det_tokens.copy()
        for tok in jieba_tokens:
            if CJK_CHAR_PATTERN.search(tok):
                merged.append(tok)

        strategy = "jieba_plus_deterministic" if self.mode == "jieba" else "auto_jieba_plus_deterministic"
        return TokenizerResult(tokens=merged, strategy_name=strategy)


class LocalBM25Index:
    def __init__(self, records: list[dict[str, Any]], tokenizer: MixedTokenizer, k1: float = 1.5, b: float = 0.75) -> None:
        self.records = records
        self.tokenizer = tokenizer
        self.k1 = k1
        self.b = b
        self.doc_tokens: list[list[str]] = []
        self.doc_term_freqs: list[Counter[str]] = []
        self.doc_lengths: list[int] = []
        self.doc_freqs: Counter[str] = Counter()
        self.avg_doc_length: float = 0.0
        self.tokenizer_strategy_used = ""
        self._build()

    def _build(self) -> None:
        for record in self.records:
            base_text = " ".join(
                [
                    str(record.get("bm25_text", "")),
                    str(record.get("chunk_text", "")),
                    str(record.get("authoritative_case_number", "")),
                ]
            )
            tokenized = self.tokenizer.tokenize(base_text)
            if not self.tokenizer_strategy_used:
                self.tokenizer_strategy_used = tokenized.strategy_name

            tokens = tokenized.tokens
            term_freq = Counter(tokens)

            self.doc_tokens.append(tokens)
            self.doc_term_freqs.append(term_freq)
            self.doc_lengths.append(len(tokens))

            for term in term_freq:
                self.doc_freqs[term] += 1

        if self.doc_lengths:
            self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths)

    def _idf(self, term: str) -> float:
        n_docs = len(self.records)
        doc_freq = self.doc_freqs.get(term, 0)
        return math.log(1 + ((n_docs - doc_freq + 0.5) / (doc_freq + 0.5)))

    @staticmethod
    def _normalize_case_for_match(case_number: str) -> str:
        return re.sub(r"\s+", "", (case_number or "").lower())

    def search(self, query: str, top_k: int = 10) -> tuple[list[RankedHit], TokenizerResult]:
        query_tokens = self.tokenizer.tokenize(query)
        if not query_tokens.tokens:
            return [], query_tokens

        query_case_refs = {
            token for token in query_tokens.tokens if "/" in token and any(ch.isdigit() for ch in token)
        }

        scored_hits: list[RankedHit] = []
        for idx, record in enumerate(self.records):
            tf = self.doc_term_freqs[idx]
            doc_len = self.doc_lengths[idx]
            score = 0.0

            for term in query_tokens.tokens:
                freq = tf.get(term, 0)
                if freq == 0:
                    continue

                idf = self._idf(term)
                numerator = freq * (self.k1 + 1)
                denominator = freq + self.k1 * (1 - self.b + self.b * doc_len / max(self.avg_doc_length, 1.0))
                score += idf * (numerator / denominator)

            authoritative_case_number = str(record.get("authoritative_case_number", ""))
            normalized_doc_case = self._normalize_case_for_match(authoritative_case_number)
            if query_case_refs and any(case_ref in normalized_doc_case for case_ref in query_case_refs):
                score += 2.0

            if score <= 0:
                continue

            preview = str(record.get("chunk_text", "")).replace("\n", " ")
            preview = re.sub(r"\s+", " ", preview).strip()
            preview = preview[:220] + ("..." if len(preview) > 220 else "")

            scored_hits.append(
                RankedHit(
                    score=score,
                    chunk_id=str(record.get("chunk_id", "")),
                    authoritative_case_number=authoritative_case_number,
                    authoritative_decision_date=str(record.get("authoritative_decision_date", "")),
                    court=str(record.get("court", "")),
                    language=str(record.get("language", "")),
                    case_type=str(record.get("case_type", "")),
                    chunk_text_preview=preview,
                    pdf_url=str(record.get("pdf_url", "")),
                    text_url_or_action=str(record.get("text_url_or_action", "")),
                )
            )

        ranked = sorted(scored_hits, key=lambda x: x.score, reverse=True)
        return ranked[: max(top_k, 1)], query_tokens


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file_obj:
        for line in file_obj:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local BM25 query prototype for Macau court corpus")
    parser.add_argument("query", type=str, help="query string")
    parser.add_argument("--top-k", type=int, default=10, help="number of top hits to return")
    parser.add_argument(
        "--tokenizer",
        choices=["deterministic", "auto", "jieba"],
        default="deterministic",
        help="tokenizer backend (default: deterministic)",
    )
    return parser.parse_args()


def write_demo_report(
    total_records: int,
    tokenizer_strategy: str,
    query: str,
    top_k: int,
    hits: list[RankedHit],
    success: bool,
) -> None:
    lines = [
        "BM25 Query Demo Report - Macau Court Cases",
        f"bm25_input_path: {BM25_CHUNKS_PATH}",
        f"total_bm25_records_loaded: {total_records}",
        f"tokenizer_strategy_used: {tokenizer_strategy}",
        f"query_received: {query}",
        f"top_k_requested: {top_k}",
        f"top_k_returned: {len(hits)}",
        f"bm25_query_prototype_successful: {success}",
        "top_hits:",
    ]

    for rank, hit in enumerate(hits, start=1):
        lines.extend(
            [
                f"  [{rank}] score={hit.score:.6f}",
                f"       chunk_id={hit.chunk_id}",
                f"       authoritative_case_number={hit.authoritative_case_number}",
                f"       authoritative_decision_date={hit.authoritative_decision_date}",
                f"       court={hit.court}",
                f"       language={hit.language}",
                f"       case_type={hit.case_type}",
                f"       chunk_text_preview={hit.chunk_text_preview}",
                f"       pdf_url={hit.pdf_url}",
                f"       text_url_or_action={hit.text_url_or_action}",
            ]
        )

    DEMO_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()

    try:
        if not BM25_CHUNKS_PATH.exists():
            raise FileNotFoundError(f"BM25 chunks file not found: {BM25_CHUNKS_PATH}")

        bm25_records = read_jsonl(BM25_CHUNKS_PATH)
        tokenizer = MixedTokenizer(mode=args.tokenizer)
        bm25_index = LocalBM25Index(records=bm25_records, tokenizer=tokenizer)
        hits, query_tokens = bm25_index.search(query=args.query, top_k=args.top_k)

        success = bool(bm25_records) and bool(query_tokens.tokens) and len(hits) > 0
        write_demo_report(
            total_records=len(bm25_records),
            tokenizer_strategy=bm25_index.tokenizer_strategy_used,
            query=args.query,
            top_k=args.top_k,
            hits=hits,
            success=success,
        )

        print(f"total bm25 records loaded: {len(bm25_records)}")
        print(f"tokenizer strategy used: {bm25_index.tokenizer_strategy_used}")
        print(f"query received: {args.query}")
        print(f"top_k returned: {len(hits)}")
        print(f"bm25 query prototype appears successful: {success}")

        for rank, hit in enumerate(hits, start=1):
            print(f"[{rank}] score={hit.score:.6f} chunk_id={hit.chunk_id} case={hit.authoritative_case_number}")
            print(
                f"      date={hit.authoritative_decision_date} court={hit.court} "
                f"language={hit.language} case_type={hit.case_type}"
            )
            print(f"      preview={hit.chunk_text_preview}")
            print(f"      pdf_url={hit.pdf_url}")
            print(f"      text_url_or_action={hit.text_url_or_action}")

    except Exception as exc:  # basic top-level error handling
        print(f"local bm25 query prototype failed: {exc}")
        raise


if __name__ == "__main__":
    main()
