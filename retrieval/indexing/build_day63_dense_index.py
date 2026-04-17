#!/usr/bin/env python3
"""Build/refresh Day 63 dense retrieval baseline artifacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from crawler.retrieval.dense_embedding_baseline import (
    BM25_CHUNKS_PATH,
    DENSE_BASELINE_ARTIFACT_PATH,
    DAY63_DENSE_MODEL_CONFIG,
    build_dense_index_artifact,
    save_dense_index_artifact,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Day 63 dense baseline artifact")
    parser.add_argument("--source", type=Path, default=BM25_CHUNKS_PATH, help="prepared chunk corpus path")
    parser.add_argument("--output", type=Path, default=DENSE_BASELINE_ARTIFACT_PATH, help="artifact path")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    artifact = build_dense_index_artifact(source_path=args.source, config=DAY63_DENSE_MODEL_CONFIG)
    save_dense_index_artifact(artifact=artifact, output_path=args.output)

    print(f"model_key: {artifact.model_key}")
    print(f"embedding_dim: {artifact.embedding_dim}")
    print(f"source_path: {artifact.source_path}")
    print(f"total_chunks: {artifact.total_chunks}")
    print(f"artifact_output: {args.output}")


if __name__ == "__main__":
    main()
