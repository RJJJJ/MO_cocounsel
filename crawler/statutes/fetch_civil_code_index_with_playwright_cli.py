#!/usr/bin/env python3
"""Fetch Macau Civil Code index page raw snapshots and line-level extraction.

Primary intent:
- use Playwright CLI to capture deterministic visual/raw snapshots
- preserve raw html/text for downstream deterministic parsing
- emit line records for LLM node_type classification
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin
from urllib.request import Request, urlopen

DEFAULT_INDEX_URL = "https://bo.io.gov.mo/bo/i/1999/31/codciv/indice_art.asp"
RAW_DIR = Path("data/raw/statutes/civil_code/index")
PARSED_DIR = Path("data/parsed/statutes/civil_code/index")


class AnchorCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.anchors: list[dict[str, str]] = []
        self._current_href = ""
        self._current_text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() == "a":
            attr_map = {k.lower(): (v or "") for k, v in attrs}
            self._current_href = attr_map.get("href", "").strip()
            self._current_text = []

    def handle_data(self, data: str) -> None:
        if self._current_href:
            self._current_text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._current_href:
            text = normalize_text("".join(self._current_text))
            self.anchors.append({"href": self._current_href, "text": text})
            self._current_href = ""
            self._current_text = []


@dataclass(frozen=True)
class LineRecord:
    line_no: int
    text: str
    source_url: str
    href: str


def normalize_text(value: str) -> str:
    value = unescape(value.replace("\u00a0", " "))
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def strip_tags(html: str) -> str:
    no_script = re.sub(r"<script[\\s\\S]*?</script>", " ", html, flags=re.IGNORECASE)
    no_style = re.sub(r"<style[\\s\\S]*?</style>", " ", no_script, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "\n", no_style)
    text = unescape(text)
    text = text.replace("\r", "\n")
    text = re.sub(r"\n{2,}", "\n", text)
    return text


def fetch_html(url: str, timeout_seconds: int) -> str:
    request = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0 Safari/537.36"
        },
    )
    with urlopen(request, timeout=timeout_seconds) as response:  # nosec B310
        return response.read().decode("utf-8", errors="replace")


def run_playwright_cli(url: str, screenshot_path: Path, timeout_ms: int) -> tuple[bool, str]:
    playwright_bin = shutil.which("playwright")
    if playwright_bin is None:
        return False, "playwright_cli_not_found"

    command = [
        playwright_bin,
        "screenshot",
        "--browser",
        "chromium",
        "--timeout",
        str(timeout_ms),
        url,
        str(screenshot_path),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    if completed.returncode != 0:
        stderr = (completed.stderr or "").strip()
        return False, f"playwright_cli_failed: {stderr}"
    return True, "ok"


def build_line_records(raw_text: str, source_url: str, anchors: list[dict[str, str]]) -> list[LineRecord]:
    anchor_map: dict[str, str] = {}
    for anchor in anchors:
        text = normalize_text(anchor.get("text", ""))
        href = normalize_text(anchor.get("href", ""))
        if text and href and text not in anchor_map:
            anchor_map[text] = urljoin(source_url, href)

    records: list[LineRecord] = []
    for idx, raw_line in enumerate(raw_text.splitlines(), start=1):
        text = normalize_text(raw_line)
        if not text:
            continue
        href = anchor_map.get(text, "")
        records.append(LineRecord(line_no=idx, text=text, source_url=source_url, href=href))
    return records


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file_obj:
        for row in rows:
            file_obj.write(json.dumps(row, ensure_ascii=False) + "\n")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch Civil Code index page with Playwright CLI snapshot.")
    parser.add_argument("--index-url", default=DEFAULT_INDEX_URL)
    parser.add_argument("--timeout-seconds", type=int, default=30)
    parser.add_argument("--playwright-timeout-ms", type=int, default=45000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PARSED_DIR.mkdir(parents=True, exist_ok=True)

    html_path = RAW_DIR / "index_raw.html"
    text_path = RAW_DIR / "index_raw.txt"
    screenshot_path = RAW_DIR / "index_raw.png"

    html = fetch_html(args.index_url, timeout_seconds=args.timeout_seconds)
    html_path.write_text(html, encoding="utf-8")

    extracted_text = strip_tags(html)
    text_path.write_text(extracted_text, encoding="utf-8")

    parser = AnchorCollector()
    parser.feed(html)

    lines = build_line_records(extracted_text, args.index_url, parser.anchors)
    line_rows = [
        {
            "line_no": row.line_no,
            "line_text": row.text,
            "source_url": row.source_url,
            "href": row.href,
        }
        for row in lines
    ]
    line_jsonl_path = PARSED_DIR / "index_lines.jsonl"
    write_jsonl(line_jsonl_path, line_rows)

    screenshot_ok, screenshot_status = run_playwright_cli(
        args.index_url,
        screenshot_path=screenshot_path,
        timeout_ms=args.playwright_timeout_ms,
    )

    report = {
        "code_id": "mo-civil-code",
        "index_url": args.index_url,
        "raw_html_path": str(html_path),
        "raw_text_path": str(text_path),
        "raw_screenshot_path": str(screenshot_path),
        "index_lines_path": str(line_jsonl_path),
        "line_count": len(line_rows),
        "anchor_count": len(parser.anchors),
        "html_sha256": sha256_text(html),
        "text_sha256": sha256_text(extracted_text),
        "playwright_cli_snapshot_ok": screenshot_ok,
        "playwright_cli_snapshot_status": screenshot_status,
    }
    report_path = PARSED_DIR / "index_fetch_report.json"
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
