"""Day 4 probe: parse search result HTML into preliminary result items.

This script intentionally stays exploratory and permissive:
- no fixed CSS selector assumption
- no Playwright usage
- no DB writes
- no full crawler pipeline
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

try:
    from bs4 import BeautifulSoup
    from bs4.element import Tag
except ModuleNotFoundError as import_error:  # pragma: no cover - environment guard
    BeautifulSoup = None  # type: ignore[assignment]
    Tag = object  # type: ignore[assignment]

INPUT_HTML_PATH = Path("data/raw/court_probe/search_attempt_last_30_days.html")
OUTPUT_DIR = Path("data/parsed/court_probe")
OUTPUT_JSON_PATH = OUTPUT_DIR / "result_items_last_30_days.json"
OUTPUT_REPORT_PATH = OUTPUT_DIR / "result_items_probe_report.txt"
BASE_URL = "https://www.court.gov.mo"

CASE_NUMBER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b\d{1,5}/\d{2,4}\b"),
    re.compile(r"\b(?:CR|CV|AC|HC|SC|PC|MP)-?\d{1,6}/\d{2,4}\b", re.IGNORECASE),
    re.compile(r"案(?:件)?編號[:：\s]*([A-Za-z0-9\-/.]+)"),
)
DATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b\d{4}[-/.年]\d{1,2}[-/.月]\d{1,2}日?\b"),
    re.compile(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{4}\b"),
)
COURT_MARKERS: tuple[str, ...] = (
    "法院",
    "法庭",
    "終審",
    "中級",
    "初級",
    "檢察",
    "Tribunal",
    "Court",
)
DETAIL_URL_HINTS: tuple[str, ...] = ("detail", "judgment", "case", "result", "view")
DOCUMENT_URL_HINTS: tuple[str, ...] = ("pdf", "download", "document", "doc", "file")


@dataclass
class ProbeStats:
    total_candidate_links: int = 0
    total_repeated_blocks: int = 0
    total_result_items: int = 0
    looks_like_real_result_page: bool = False
    looks_like_search_form_again: bool = False


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def first_match(patterns: Iterable[re.Pattern[str]], text: str) -> str | None:
    for pattern in patterns:
        match = pattern.search(text)
        if match:
            if match.groups():
                return normalize_space(match.group(1))
            return normalize_space(match.group(0))
    return None


def detect_search_form_signals(soup: BeautifulSoup) -> bool:
    forms = soup.find_all("form")
    if not forms:
        return False

    page_text = normalize_space(soup.get_text(" ", strip=True))
    marker_hits = sum(
        marker in page_text
        for marker in ("裁判書搜尋", "搜尋", "宣判日期", "案件編號", "查詢")
    )
    return marker_hits >= 2


def find_candidate_links(soup: BeautifulSoup) -> list[Tag]:
    links: list[Tag] = []
    for anchor in soup.find_all("a", href=True):
        href = anchor.get("href", "")
        text = normalize_space(anchor.get_text(" ", strip=True))
        if not href:
            continue

        is_case_like = bool(first_match(CASE_NUMBER_PATTERNS, text))
        has_doc_hint = any(hint in href.lower() for hint in DOCUMENT_URL_HINTS)
        has_detail_hint = any(hint in href.lower() for hint in DETAIL_URL_HINTS)

        if is_case_like or has_doc_hint or has_detail_hint or len(text) >= 14:
            links.append(anchor)
    return links


def signature_for_block(tag: Tag) -> str:
    classes = ".".join(sorted(tag.get("class", [])))
    return f"{tag.name}|{classes}" if classes else tag.name


def find_repeated_blocks(soup: BeautifulSoup) -> list[Tag]:
    candidate_tags = soup.find_all(["tr", "li", "article", "section", "div"])
    signatures = Counter(signature_for_block(tag) for tag in candidate_tags)

    repeated: list[Tag] = []
    for tag in candidate_tags:
        sig = signature_for_block(tag)
        if signatures[sig] < 3:
            continue

        text = normalize_space(tag.get_text(" ", strip=True))
        if len(text) < 40:
            continue
        repeated.append(tag)

    return repeated


def classify_links(block: Tag) -> tuple[str | None, str | None]:
    detail_url: str | None = None
    document_url: str | None = None

    for anchor in block.find_all("a", href=True):
        href = urljoin(BASE_URL, anchor["href"])
        href_l = href.lower()

        if document_url is None and any(h in href_l for h in DOCUMENT_URL_HINTS):
            document_url = href
            continue

        if detail_url is None and any(h in href_l for h in DETAIL_URL_HINTS):
            detail_url = href
            continue

        if detail_url is None:
            detail_url = href

    return detail_url, document_url


def parse_result_item(block: Tag) -> dict[str, str | None]:
    raw_text = normalize_space(block.get_text(" ", strip=True))
    title = None

    heading = block.find(["h1", "h2", "h3", "h4", "strong", "b"]) or block.find("a")
    if heading:
        title = normalize_space(heading.get_text(" ", strip=True)) or None

    case_number = first_match(CASE_NUMBER_PATTERNS, raw_text)
    judgment_date = first_match(DATE_PATTERNS, raw_text)

    court = None
    for marker in COURT_MARKERS:
        pos = raw_text.find(marker)
        if pos >= 0:
            court = normalize_space(raw_text[max(0, pos - 12) : pos + 16])
            break

    detail_url, document_url = classify_links(block)

    return {
        "raw_text": raw_text or None,
        "title": title,
        "case_number": case_number,
        "judgment_date": judgment_date,
        "court": court,
        "detail_url": detail_url,
        "document_url": document_url,
    }


def deduplicate_items(items: list[dict[str, str | None]]) -> list[dict[str, str | None]]:
    seen: set[tuple[str | None, str | None, str | None]] = set()
    output: list[dict[str, str | None]] = []

    for item in items:
        key = (item.get("title"), item.get("case_number"), item.get("raw_text"))
        if key in seen:
            continue
        seen.add(key)
        output.append(item)

    return output


def assess_result_likelihood(
    soup: BeautifulSoup,
    items: list[dict[str, str | None]],
    repeated_blocks: list[Tag],
    candidate_links: list[Tag],
) -> bool:
    if len(items) >= 3:
        return True

    case_hits = sum(1 for i in items if i.get("case_number"))
    date_hits = sum(1 for i in items if i.get("judgment_date"))

    if case_hits >= 2 and len(repeated_blocks) >= 3:
        return True

    if len(candidate_links) > 15 and date_hits >= 2:
        return True

    page_text = normalize_space(soup.get_text(" ", strip=True))
    no_result_markers = ("沒有資料", "查無", "No result", "No records")
    if any(marker in page_text for marker in no_result_markers):
        return False

    return False


def build_report(stats: ProbeStats, items: list[dict[str, str | None]]) -> str:
    lines = [
        "# Court result list probe report (Day 4)",
        f"input_html: {INPUT_HTML_PATH}",
        f"output_json: {OUTPUT_JSON_PATH}",
        "",
        f"total candidate links found: {stats.total_candidate_links}",
        f"total repeated blocks found: {stats.total_repeated_blocks}",
        f"total result items extracted: {stats.total_result_items}",
        f"whether page looks like real result page: {stats.looks_like_real_result_page}",
        (
            "whether page looks like same search form page returned again: "
            f"{stats.looks_like_search_form_again}"
        ),
        "",
        "sample extracted items (up to first 5):",
    ]

    for idx, item in enumerate(items[:5], start=1):
        lines.append(f"- item {idx}: {json.dumps(item, ensure_ascii=False)}")

    if not items:
        lines.append("- (none)")

    lines.append("")
    lines.append("note: this is a probe output, not production parser logic.")
    return "\n".join(lines)


def run_probe() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if BeautifulSoup is None:
        OUTPUT_JSON_PATH.write_text("[]\n", encoding="utf-8")
        OUTPUT_REPORT_PATH.write_text(
            "# Court result list probe report (Day 4)\n"
            f"input_html: {INPUT_HTML_PATH}\n"
            "error: missing dependency bs4 (BeautifulSoup).\n",
            encoding="utf-8",
        )
        print("total candidate links found: 0")
        print("total repeated blocks found: 0")
        print("total result items extracted: 0")
        print("whether page looks like real result page: False")
        print("whether page looks like same search form page returned again: False")
        print("error: missing dependency bs4 (BeautifulSoup)")
        return 3

    if not INPUT_HTML_PATH.exists():
        stats = ProbeStats(looks_like_search_form_again=False, looks_like_real_result_page=False)
        empty_report = build_report(stats=stats, items=[])
        OUTPUT_JSON_PATH.write_text("[]\n", encoding="utf-8")
        OUTPUT_REPORT_PATH.write_text(
            empty_report + "\nerror: input html file not found.\n", encoding="utf-8"
        )

        print("total candidate links found: 0")
        print("total repeated blocks found: 0")
        print("total result items extracted: 0")
        print("whether page looks like real result page: False")
        print("whether page looks like same search form page returned again: False")
        print(f"error: input file missing at {INPUT_HTML_PATH}")
        return 1

    try:
        html = INPUT_HTML_PATH.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        html = INPUT_HTML_PATH.read_text(encoding="big5", errors="ignore")
    except OSError as exc:
        print(f"error: failed reading input html: {exc}")
        return 2

    soup = BeautifulSoup(html, "html.parser")

    candidate_links = find_candidate_links(soup)
    repeated_blocks = find_repeated_blocks(soup)

    parsed_items = [parse_result_item(block) for block in repeated_blocks]
    parsed_items = [item for item in parsed_items if item.get("raw_text")]
    parsed_items = deduplicate_items(parsed_items)

    looks_like_form_again = detect_search_form_signals(soup)
    looks_like_result_page = assess_result_likelihood(
        soup=soup,
        items=parsed_items,
        repeated_blocks=repeated_blocks,
        candidate_links=candidate_links,
    )

    stats = ProbeStats(
        total_candidate_links=len(candidate_links),
        total_repeated_blocks=len(repeated_blocks),
        total_result_items=len(parsed_items),
        looks_like_real_result_page=looks_like_result_page,
        looks_like_search_form_again=looks_like_form_again,
    )

    OUTPUT_JSON_PATH.write_text(
        json.dumps(parsed_items, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    OUTPUT_REPORT_PATH.write_text(build_report(stats=stats, items=parsed_items) + "\n", encoding="utf-8")

    print(f"total candidate links found: {stats.total_candidate_links}")
    print(f"total repeated blocks found: {stats.total_repeated_blocks}")
    print(f"total result items extracted: {stats.total_result_items}")
    print(f"whether page looks like real result page: {stats.looks_like_real_result_page}")
    print(
        "whether page looks like same search form page returned again: "
        f"{stats.looks_like_search_form_again}"
    )
    print(f"saved_json: {OUTPUT_JSON_PATH}")
    print(f"saved_report: {OUTPUT_REPORT_PATH}")
    return 0


def main() -> None:
    raise SystemExit(run_probe())


if __name__ == "__main__":
    main()
