"""Day 2 source connectivity probe for Macau Court judgment search page.

This script intentionally implements a minimal probe only:
- single GET request with requests
- basic response metadata logging
- keyword presence checks
- raw HTML + plain-text preview persistence

No crawler workflow, DB write, or API integration is included.
"""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

import requests
from bs4 import BeautifulSoup

TARGET_URL = "https://www.court.gov.mo/zh/subpage/researchjudgments"
OUTPUT_DIR = Path("data/raw/court_probe")
HTML_OUTPUT_PATH = OUTPUT_DIR / "researchjudgments.html"
TEXT_PREVIEW_OUTPUT_PATH = OUTPUT_DIR / "researchjudgments_text_preview.txt"
KEYWORDS: tuple[str, ...] = (
    "裁判書搜尋",
    "法院",
    "種類",
    "案件編號",
    "宣判日期",
    "裁判書全文",
)


def extract_visible_text(html: str) -> str:
    """Extract visible text from HTML for quick human inspection."""
    soup = BeautifulSoup(html, "html.parser")

    for tag in soup(["script", "style", "noscript", "meta", "link"]):
        tag.decompose()

    lines: list[str] = []
    for fragment in soup.stripped_strings:
        text = fragment.strip()
        if text:
            lines.append(text)
    return "\n".join(lines)


def print_keyword_presence(content: str, keywords: Iterable[str]) -> None:
    for keyword in keywords:
        exists = keyword in content
        print(f"keyword[{keyword}]: {'YES' if exists else 'NO'}")


def run_probe() -> int:
    """Execute connectivity probe and persist artifacts.

    Returns:
        int: process-style return code (0 for success, non-zero for failure).
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }

    try:
        response = requests.get(TARGET_URL, timeout=30, headers=headers)
        response.raise_for_status()
    except requests.RequestException as exc:
        print("Probe failed during HTTP GET request.")
        print(f"error: {exc}")
        return 1

    content_type = response.headers.get("content-type", "<missing>")
    html = response.text

    print(f"status_code: {response.status_code}")
    print(f"content_type: {content_type}")
    print(f"final_url: {response.url}")
    print(f"response_encoding: {response.encoding}")
    print(f"html_length: {len(html)}")
    print_keyword_presence(html, KEYWORDS)

    try:
        HTML_OUTPUT_PATH.write_text(html, encoding=response.encoding or "utf-8")
    except OSError as exc:
        print(f"Failed to write HTML output: {exc}")
        return 2

    text_preview = extract_visible_text(html)
    try:
        TEXT_PREVIEW_OUTPUT_PATH.write_text(text_preview, encoding="utf-8")
    except OSError as exc:
        print(f"Failed to write text preview output: {exc}")
        return 3

    print(f"saved_html: {HTML_OUTPUT_PATH}")
    print(f"saved_text_preview: {TEXT_PREVIEW_OUTPUT_PATH}")
    return 0


def main() -> None:
    raise SystemExit(run_probe())


if __name__ == "__main__":
    main()
