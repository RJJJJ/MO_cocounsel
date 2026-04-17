#!/usr/bin/env python3
"""Day 63 dense retrieval baseline over prepared authoritative chunk corpus.

Design constraints:
- Keep BM25 path unchanged; this module is a parallel dense-only baseline.
- Use a deterministic local embedding baseline with zero heavy dependencies.
- Support Chinese/Portuguese/mixed queries via unicode char n-gram hashing.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from crawler.retrieval.local_bm25_query_prototype import BM25_CHUNKS_PATH, read_jsonl

DENSE_BASELINE_ROOT = Path("data/corpus/prepared/macau_court_cases/dense_baseline")
DENSE_BASELINE_ARTIFACT_PATH = DENSE_BASELINE_ROOT / "day63_dense_index.json"


@dataclass(frozen=True)
class DenseBaselineModelConfig:
    model_key: str
    embedding_dim: int
    char_ngram_min: int
    char_ngram_max: int
    include_unigram_for_cjk: bool


DAY63_DENSE_MODEL_CONFIG = DenseBaselineModelConfig(
    model_key="chargram_hash_v1",
    embedding_dim=768,
    char_ngram_min=2,
    char_ngram_max=4,
    include_unigram_for_cjk=True,
)


@dataclass(frozen=True)
class DenseSearchHit:
    chunk_id: str
    score: float
    authoritative_case_number: str
    authoritative_decision_date: str
    court: str
    language: str
    case_type: str
    chunk_text_preview: str
    pdf_url: str
    text_url_or_action: str


@dataclass(frozen=True)
class DenseIndexArtifact:
    artifact_version: str
    model_key: str
    embedding_dim: int
    source_path: str
    total_chunks: int
    records: list[dict[str, Any]]


class HashCharNgramEmbedder:
    """Deterministic multilingual embedder via hashed char n-grams.

    This intentionally trades absolute quality for local feasibility and
    reproducibility in constrained runtime environments.
    """

    _CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")

    def __init__(self, config: DenseBaselineModelConfig) -> None:
        self._config = config

    @staticmethod
    def _normalize(text: str) -> str:
        normalized = unicodedata.normalize("NFKC", text or "")
        normalized = normalized.replace("\r\n", "\n").replace("\r", "\n")
        return normalized.lower().strip()

    def _iter_ngrams(self, text: str) -> list[str]:
        normalized = self._normalize(text)
        if not normalized:
            return []

        chars = [ch for ch in normalized if not ch.isspace()]
        if not chars:
            return []

        grams: list[str] = []
        for n in range(self._config.char_ngram_min, self._config.char_ngram_max + 1):
            if len(chars) < n:
                continue
            for idx in range(len(chars) - n + 1):
                grams.append("".join(chars[idx : idx + n]))

        if self._config.include_unigram_for_cjk:
            grams.extend(ch for ch in chars if self._CJK_PATTERN.match(ch))

        return grams

    def encode(self, text: str) -> list[float]:
        grams = self._iter_ngrams(text)
        vec = [0.0] * self._config.embedding_dim
        if not grams:
            return vec

        for gram in grams:
            digest = hashlib.blake2b(gram.encode("utf-8"), digest_size=8).digest()
            bucket = int.from_bytes(digest[:4], byteorder="big") % self._config.embedding_dim
            sign = 1.0 if (digest[4] % 2 == 0) else -1.0
            vec[bucket] += sign

        norm = math.sqrt(sum(v * v for v in vec))
        if norm <= 0:
            return vec
        return [v / norm for v in vec]


class LocalDenseBaselineIndex:
    def __init__(self, artifact: DenseIndexArtifact, embedder: HashCharNgramEmbedder) -> None:
        self._artifact = artifact
        self._embedder = embedder

    @property
    def model_key(self) -> str:
        return self._artifact.model_key

    @property
    def total_chunks(self) -> int:
        return self._artifact.total_chunks

    def search(self, query: str, top_k: int) -> list[DenseSearchHit]:
        query_vec = self._embedder.encode(query)
        if not any(query_vec):
            return []

        scored_hits: list[DenseSearchHit] = []
        for record in self._artifact.records:
            doc_vec = record.get("embedding", [])
            if not doc_vec:
                continue
            score = sum(float(a) * float(b) for a, b in zip(query_vec, doc_vec, strict=False))
            if score <= 0:
                continue

            scored_hits.append(
                DenseSearchHit(
                    chunk_id=str(record.get("chunk_id", "")),
                    score=score,
                    authoritative_case_number=str(record.get("authoritative_case_number", "")),
                    authoritative_decision_date=str(record.get("authoritative_decision_date", "")),
                    court=str(record.get("court", "")),
                    language=str(record.get("language", "")),
                    case_type=str(record.get("case_type", "")),
                    chunk_text_preview=str(record.get("chunk_text_preview", "")),
                    pdf_url=str(record.get("pdf_url", "")),
                    text_url_or_action=str(record.get("text_url_or_action", "")),
                )
            )

        ranked = sorted(scored_hits, key=lambda item: item.score, reverse=True)
        return ranked[: max(top_k, 1)]


def _record_text_for_embedding(record: dict[str, Any]) -> str:
    fields = [
        str(record.get("authoritative_case_number", "")),
        str(record.get("case_type", "")),
        str(record.get("court", "")),
        str(record.get("language", "")),
        str(record.get("bm25_text", "")),
        str(record.get("chunk_text", "")),
    ]
    return "\n".join(field for field in fields if field)


def _chunk_preview(text: str, max_len: int = 220) -> str:
    compact = re.sub(r"\s+", " ", (text or "").replace("\n", " ")).strip()
    return compact[:max_len] + ("..." if len(compact) > max_len else "")


def build_dense_index_artifact(
    source_path: Path = BM25_CHUNKS_PATH,
    config: DenseBaselineModelConfig = DAY63_DENSE_MODEL_CONFIG,
) -> DenseIndexArtifact:
    records = read_jsonl(source_path)
    embedder = HashCharNgramEmbedder(config=config)

    artifact_records: list[dict[str, Any]] = []
    for record in records:
        dense_text = _record_text_for_embedding(record)
        embedding = embedder.encode(dense_text)
        artifact_records.append(
            {
                "chunk_id": str(record.get("chunk_id", "")),
                "authoritative_case_number": str(record.get("authoritative_case_number", "")),
                "authoritative_decision_date": str(record.get("authoritative_decision_date", "")),
                "court": str(record.get("court", "")),
                "language": str(record.get("language", "")),
                "case_type": str(record.get("case_type", "")),
                "chunk_text_preview": _chunk_preview(str(record.get("chunk_text", ""))),
                "pdf_url": str(record.get("pdf_url", "")),
                "text_url_or_action": str(record.get("text_url_or_action", "")),
                "embedding": embedding,
            }
        )

    return DenseIndexArtifact(
        artifact_version="day63_dense_baseline_v1",
        model_key=config.model_key,
        embedding_dim=config.embedding_dim,
        source_path=str(source_path),
        total_chunks=len(artifact_records),
        records=artifact_records,
    )


def save_dense_index_artifact(artifact: DenseIndexArtifact, output_path: Path = DENSE_BASELINE_ARTIFACT_PATH) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "artifact_version": artifact.artifact_version,
        "model_key": artifact.model_key,
        "embedding_dim": artifact.embedding_dim,
        "source_path": artifact.source_path,
        "total_chunks": artifact.total_chunks,
        "records": artifact.records,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def load_dense_index_artifact(path: Path = DENSE_BASELINE_ARTIFACT_PATH) -> DenseIndexArtifact:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return DenseIndexArtifact(
        artifact_version=str(payload["artifact_version"]),
        model_key=str(payload["model_key"]),
        embedding_dim=int(payload["embedding_dim"]),
        source_path=str(payload["source_path"]),
        total_chunks=int(payload["total_chunks"]),
        records=list(payload["records"]),
    )


def build_or_load_dense_index(
    artifact_path: Path = DENSE_BASELINE_ARTIFACT_PATH,
    source_path: Path = BM25_CHUNKS_PATH,
    config: DenseBaselineModelConfig = DAY63_DENSE_MODEL_CONFIG,
    rebuild: bool = False,
) -> LocalDenseBaselineIndex:
    if rebuild or not artifact_path.exists():
        artifact = build_dense_index_artifact(source_path=source_path, config=config)
        save_dense_index_artifact(artifact=artifact, output_path=artifact_path)
    else:
        artifact = load_dense_index_artifact(path=artifact_path)

    embedder = HashCharNgramEmbedder(config=config)
    return LocalDenseBaselineIndex(artifact=artifact, embedder=embedder)
