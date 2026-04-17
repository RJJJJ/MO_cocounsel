#!/usr/bin/env python3
"""Day 63B dense retrieval baseline with bge-m3 over refreshed chunk corpus."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from crawler.prep.build_day63b_dense_ready_chunks import DAY63B_DENSE_READY_CHUNKS_PATH
from crawler.retrieval.local_bm25_query_prototype import read_jsonl

DAY63B_DENSE_BASELINE_ROOT = Path("data/corpus/prepared/macau_court_cases/dense_baseline")
DAY63B_DENSE_ARTIFACT_PATH = DAY63B_DENSE_BASELINE_ROOT / "day63b_bge_m3_index.json"


@dataclass(frozen=True)
class Day63BDenseModelConfig:
    model_key: str
    hf_model_name: str
    embedding_dim: int
    batch_size: int
    max_length: int


DAY63B_DENSE_MODEL_CONFIG = Day63BDenseModelConfig(
    model_key="day63b_bge_m3",
    hf_model_name="BAAI/bge-m3",
    embedding_dim=1024,
    batch_size=4,
    max_length=8192,
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


class BgeM3Embedder:
    """Thin wrapper around FlagEmbedding BGEM3FlagModel.

    Day 63B keeps setup lightweight: this wrapper requires only FlagEmbedding
    at runtime and performs CPU-friendly small-batch encoding.
    """

    def __init__(self, config: Day63BDenseModelConfig) -> None:
        self._config = config
        try:
            from FlagEmbedding import BGEM3FlagModel  # type: ignore
        except Exception as exc:  # pragma: no cover - dependency guard
            raise RuntimeError(
                "FlagEmbedding is required for Day63B bge-m3 baseline. "
                "Install dependencies locally (e.g., FlagEmbedding + torch + transformers) "
                "before building/searching this index."
            ) from exc

        self._model = BGEM3FlagModel(
            config.hf_model_name,
            use_fp16=False,
            devices="cpu",
        )

    def encode_batch(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        encoded = self._model.encode(
            texts,
            batch_size=self._config.batch_size,
            max_length=self._config.max_length,
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False,
        )
        vectors = encoded.get("dense_vecs")
        if vectors is None:
            return []
        return [list(map(float, vec)) for vec in vectors]

    def encode(self, text: str) -> list[float]:
        rows = self.encode_batch([text])
        return rows[0] if rows else [0.0] * self._config.embedding_dim


class LocalDenseBaselineIndex:
    def __init__(self, artifact: DenseIndexArtifact, embedder: BgeM3Embedder) -> None:
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


def build_embedding_text(record: dict[str, Any]) -> str:
    parts = [
        f"case_number: {record.get('authoritative_case_number', '')}",
        f"court: {record.get('court', '')}",
        f"language: {record.get('language', '')}",
        f"case_type: {record.get('case_type', '')}",
        "chunk_text:",
        str(record.get("chunk_text", "")),
    ]
    return "\n".join(part for part in parts if part)


def _chunk_preview(text: str, max_len: int = 220) -> str:
    compact = re.sub(r"\s+", " ", (text or "").replace("\n", " ")).strip()
    return compact[:max_len] + ("..." if len(compact) > max_len else "")


def _l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector))
    if norm <= 0:
        return vector
    return [v / norm for v in vector]


def build_dense_index_artifact(
    source_path: Path = DAY63B_DENSE_READY_CHUNKS_PATH,
    config: Day63BDenseModelConfig = DAY63B_DENSE_MODEL_CONFIG,
) -> DenseIndexArtifact:
    rows = read_jsonl(source_path)
    embedder = BgeM3Embedder(config=config)

    texts = [build_embedding_text(row) for row in rows]
    vectors: list[list[float]] = []
    for i in range(0, len(texts), config.batch_size):
        vectors.extend(embedder.encode_batch(texts[i : i + config.batch_size]))

    artifact_rows: list[dict[str, Any]] = []
    for row, embedding in zip(rows, vectors, strict=False):
        artifact_rows.append(
            {
                "chunk_id": str(row.get("chunk_id", "")),
                "authoritative_case_number": str(row.get("authoritative_case_number", "")),
                "authoritative_decision_date": str(row.get("authoritative_decision_date", "")),
                "court": str(row.get("court", "")),
                "language": str(row.get("language", "")),
                "case_type": str(row.get("case_type", "")),
                "chunk_text_preview": _chunk_preview(str(row.get("chunk_text", ""))),
                "pdf_url": str(row.get("pdf_url", "")),
                "text_url_or_action": str(row.get("text_url_or_action", "")),
                "embedding": _l2_normalize(list(map(float, embedding))),
            }
        )

    return DenseIndexArtifact(
        artifact_version="day63b_dense_baseline_v2",
        model_key=config.model_key,
        embedding_dim=config.embedding_dim,
        source_path=str(source_path),
        total_chunks=len(artifact_rows),
        records=artifact_rows,
    )


def save_dense_index_artifact(artifact: DenseIndexArtifact, output_path: Path = DAY63B_DENSE_ARTIFACT_PATH) -> None:
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


def load_dense_index_artifact(path: Path = DAY63B_DENSE_ARTIFACT_PATH) -> DenseIndexArtifact:
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
    artifact_path: Path = DAY63B_DENSE_ARTIFACT_PATH,
    source_path: Path = DAY63B_DENSE_READY_CHUNKS_PATH,
    config: Day63BDenseModelConfig = DAY63B_DENSE_MODEL_CONFIG,
    rebuild: bool = False,
) -> LocalDenseBaselineIndex:
    if rebuild or not artifact_path.exists():
        artifact = build_dense_index_artifact(source_path=source_path, config=config)
        save_dense_index_artifact(artifact=artifact, output_path=artifact_path)
    else:
        artifact = load_dense_index_artifact(path=artifact_path)

    embedder = BgeM3Embedder(config=config)
    return LocalDenseBaselineIndex(artifact=artifact, embedder=embedder)
