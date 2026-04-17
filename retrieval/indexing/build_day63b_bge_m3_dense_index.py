#!/usr/bin/env python3
"""Build Day 63B dense-ready chunks and bge-m3 dense index artifact."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from crawler.prep.build_day63b_dense_ready_chunks import (
    DAY63B_DENSE_READY_CHUNKS_PATH,
    FULL_CORPUS_ROOT,
    FULL_MANIFEST_PATH,
    build_day63b_dense_ready_chunks,
)
from crawler.retrieval.day63b_bge_m3_dense import (
    DAY63B_DENSE_ARTIFACT_PATH,
    DAY63B_DENSE_MODEL_CONFIG,
    build_dense_index_artifact,
    save_dense_index_artifact,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Day63B bge-m3 dense baseline artifact")
    parser.add_argument("--source-root", type=Path, default=FULL_CORPUS_ROOT)
    parser.add_argument("--manifest", type=Path, default=FULL_MANIFEST_PATH)
    parser.add_argument("--dense-ready-output", type=Path, default=DAY63B_DENSE_READY_CHUNKS_PATH)
    parser.add_argument("--source", type=Path, default=DAY63B_DENSE_READY_CHUNKS_PATH)
    parser.add_argument("--output", type=Path, default=DAY63B_DENSE_ARTIFACT_PATH)
    parser.add_argument("--skip-refresh-dense-ready", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not args.skip_refresh_dense_ready:
        dense_ready_summary = build_day63b_dense_ready_chunks(
            source_root=args.source_root,
            manifest_path=args.manifest,
            output_path=args.dense_ready_output,
        )
        print(f"dense_ready_total_cases: {dense_ready_summary['total_cases']}")
        print(f"dense_ready_total_chunks: {dense_ready_summary['total_chunks']}")
        print(f"dense_ready_success: {dense_ready_summary['success']}")

    artifact = build_dense_index_artifact(source_path=args.source, config=DAY63B_DENSE_MODEL_CONFIG)
    save_dense_index_artifact(artifact=artifact, output_path=args.output)

    print(f"model_key: {artifact.model_key}")
    print(f"embedding_dim: {artifact.embedding_dim}")
    print(f"source_path: {artifact.source_path}")
    print(f"total_chunks: {artifact.total_chunks}")
    print(f"artifact_output: {args.output}")


if __name__ == "__main__":
    main()
