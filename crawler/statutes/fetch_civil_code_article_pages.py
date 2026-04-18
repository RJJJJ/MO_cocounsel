#!/usr/bin/env python3
"""Fetch Civil Code article pages discovered from index hierarchy."""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ARTICLE_INDEX_PATH = Path("data/parsed/statutes/civil_code/index/article_index.jsonl")
RAW_ARTICLE_DIR = Path("data/raw/statutes/civil_code/articles")
FETCH_LOG_PATH = Path("data/parsed/statutes/civil_code/articles/article_fetch_log.jsonl")


def load_jsonl(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as file_obj:
        for raw in file_obj:
            raw = raw.strip()
            if not raw:
                continue
            rows.append(json.loads(raw))
    return rows


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_obj:
        for row in rows:
            file_obj.write(json.dumps(row, ensure_ascii=False) + "\n")


def safe_filename(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path or "article"
    query = parsed.query or ""
    value = f"{path}?{query}" if query else path
    value = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_")
    return value[:120] or "article"


def fetch_url(url: str, timeout_seconds: int) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310
        return response.read().decode("utf-8", errors="replace")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Civil Code article pages discovered from index.")
    parser.add_argument("--article-index-path", type=Path, default=ARTICLE_INDEX_PATH)
    parser.add_argument("--output-dir", type=Path, default=RAW_ARTICLE_DIR)
    parser.add_argument("--fetch-log-path", type=Path, default=FETCH_LOG_PATH)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--max-pages", type=int, default=50)
    parser.add_argument("--sleep-seconds", type=float, default=0.8)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    rows = load_jsonl(args.article_index_path)

    unique_urls: list[str] = []
    seen: set[str] = set()
    for row in rows:
        url = str(row.get("article_url", "")).strip()
        if not url or url in seen:
            continue
        seen.add(url)
        unique_urls.append(url)

    if args.max_pages > 0:
        unique_urls = unique_urls[: args.max_pages]

    args.output_dir.mkdir(parents=True, exist_ok=True)

    fetch_rows: list[dict] = []
    for idx, url in enumerate(unique_urls, start=1):
        file_stub = safe_filename(url)
        html_path = args.output_dir / f"{idx:04d}_{file_stub}.html"
        try:
            html = fetch_url(url, timeout_seconds=args.timeout_seconds)
            html_path.write_text(html, encoding="utf-8")
            status = "ok"
            error = ""
        except Exception as exc:  # noqa: BLE001
            status = "error"
            error = str(exc)

        fetch_rows.append(
            {
                "order_index": idx,
                "source_url": url,
                "html_path": str(html_path),
                "status": status,
                "error": error,
            }
        )
        time.sleep(max(args.sleep_seconds, 0.0))

    write_jsonl(args.fetch_log_path, fetch_rows)

    summary = {
        "article_index_path": str(args.article_index_path),
        "output_dir": str(args.output_dir),
        "fetch_log_path": str(args.fetch_log_path),
        "requested_count": len(unique_urls),
        "success_count": sum(1 for row in fetch_rows if row["status"] == "ok"),
        "failed_count": sum(1 for row in fetch_rows if row["status"] != "ok"),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
