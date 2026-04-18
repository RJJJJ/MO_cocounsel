#!/usr/bin/env python3
"""Build manifest for Civil Code prototype corpus artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

HIERARCHY_PATH = Path("data/parsed/statutes/civil_code/index/hierarchy_nodes.jsonl")
ARTICLE_JSONL_PATH = Path("data/parsed/statutes/civil_code/articles/articles_structured.jsonl")
MANIFEST_PATH = Path("data/parsed/statutes/civil_code/manifest/civil_code_manifest_v1.json")


def count_jsonl_rows(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8") as file_obj:
        for raw in file_obj:
            if raw.strip():
                count += 1
    return count


def sha256_file(path: Path) -> str:
    if not path.exists():
        return ""
    digest = hashlib.sha256()
    with path.open("rb") as file_obj:
        while True:
            chunk = file_obj.read(65536)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build Civil Code corpus prototype manifest.")
    parser.add_argument("--hierarchy-path", type=Path, default=HIERARCHY_PATH)
    parser.add_argument("--article-jsonl-path", type=Path, default=ARTICLE_JSONL_PATH)
    parser.add_argument("--manifest-path", type=Path, default=MANIFEST_PATH)
    parser.add_argument("--code-id", default="mo-civil-code")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    hierarchy_count = count_jsonl_rows(args.hierarchy_path)
    article_count = count_jsonl_rows(args.article_jsonl_path)

    manifest: dict[str, Any] = {
        "manifest_version": "v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "code_id": args.code_id,
        "code_name_zh": "澳門民法典",
        "language": "pt",
        "scope": "statute-ingestion-structuring-prototype",
        "artifacts": {
            "hierarchy_nodes": {
                "path": str(args.hierarchy_path),
                "rows": hierarchy_count,
                "sha256": sha256_file(args.hierarchy_path),
            },
            "article_units": {
                "path": str(args.article_jsonl_path),
                "rows": article_count,
                "sha256": sha256_file(args.article_jsonl_path),
            },
        },
        "structured_statute_unit_schema": [
            "code_id",
            "code_name_zh",
            "article_canonical_id",
            "article_number",
            "article_heading",
            "hierarchy_path",
            "article_text",
            "language",
            "source_url",
            "parse_method",
            "confidence",
            "needs_review",
        ],
        "hierarchy_node_schema": [
            "node_type",
            "label",
            "title",
            "hierarchy_path",
            "order_index",
            "source_url",
        ],
        "next_step_notes": [
            "Prototype excludes statute dense retrieval and reranker by design.",
            "Prototype is compatible with future mixed-mode article grounding.",
        ],
    }

    args.manifest_path.parent.mkdir(parents=True, exist_ok=True)
    args.manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
