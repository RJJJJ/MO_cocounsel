"""Statute corpus loaders for local exact lookup."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

STATUTES_DIR = Path("data/corpus/raw/statutes")
STATUTE_SUMMARY_PATH = STATUTES_DIR / "statute_summary.json"
STATUTE_EXACT_LOOKUP_PATH = STATUTES_DIR / "statute_exact_lookup.json"
ARTICLES_JSONL_PATH = STATUTES_DIR / "articles.jsonl"


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as file:
        for line in file:
            text = line.strip()
            if not text:
                continue
            records.append(json.loads(text))
    return records


def load_statute_summary(path: Path = STATUTE_SUMMARY_PATH) -> Any:
    if not path.exists():
        raise FileNotFoundError(f"statute summary file not found: {path}")
    return load_json(path)


def load_statute_exact_lookup(path: Path = STATUTE_EXACT_LOOKUP_PATH) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"statute exact lookup file not found: {path}")
    data = load_json(path)
    if not isinstance(data, dict):
        raise ValueError(f"expected dict in {path}, got {type(data).__name__}")
    return data


def load_articles(path: Path = ARTICLES_JSONL_PATH) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return load_jsonl(path)
