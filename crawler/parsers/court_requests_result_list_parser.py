"""Day 8 probe: parse requests-replay result page into structured result items.

Scope:
- exploratory parser only (not production)
- BeautifulSoup-based
- no Playwright
- no database writes
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Iterable
from urllib.parse import urljoin

try:
    from bs4 import BeautifulSoup
    from bs4.element import Tag
except ModuleNotFoundError:  # pragma: no cover - environment dependency guard
    BeautifulSoup = None  # type: ignore[assignment]
    Tag = object  # type: ignore[assignment]

INPUT_HTML_PATH = Path("data/raw/court_probe/requests_replay_after_submit.html")
OUTPUT_DIR = Path("data/parsed/court_probe")
OUTPUT_JSON_PATH = OUTPUT_DIR / "requests_result_items.json"
OUTPUT_REPORT_PATH = OUTPUT_DIR / "requests_result_items_report.txt"
BASE_URL = "https://www.court.gov.mo"

CASE_NUMBER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b\d{1,6}/\d{2,4}\b"),
    re.compile(r"\b(?:CR|CV|AC|HC|SC|PC|MP|TSI|TUI)-?\d{1,6}/\d{2,4}\b", re.IGNORECASE),
    re.compile(r"案(?:件)?(?:編號|號)?[:：\s]*([A-Za-z0-9\-/.]+)"),
)
DATE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b\d{4}[./-]\d{1,2}[./-]\d{1,2}\b"),
    re.compile(r"\b\d{1,2}[./-]\d{1,2}[./-]\d{4}\b"),
    re.compile(r"\b\d{4}年\d{1,2}月\d{1,2}日\b"),
)
COURT_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(終審法院|中級法院|初級法院|行政法院|法院|法庭)"),
    re.compile(r"(Court of Final Appeal|Court of Second Instance|Court of First Instance|Court)", re.IGNORECASE),
)
DETAIL_HINTS: tuple[str, ...] = ("detail", "judgment", "searchresult", "subpage", "view", "case")
DOC_HINTS: tuple[str, ...] = (".pdf", "pdf", "download", "document", "file")


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def first_match(patterns: Iterable[re.Pattern[str]], text: str) -> str | None:
    for pattern in patterns:
        m = pattern.search(text)
        if not m:
            continue
        if m.groups():
            return normalize_space(m.group(1))
        return normalize_space(m.group(0))
    return None


def signature(tag: Tag) -> str:
    classes = ".".join(sorted(tag.get("class", [])))
    if classes:
        return f"{tag.name}|{classes}"
    return tag.name


def looks_result_like(text: str, links_count: int) -> bool:
    if len(text) < 20:
        return False
    if first_match(CASE_NUMBER_PATTERNS, text):
        return True
    if first_match(DATE_PATTERNS, text) and links_count > 0:
        return True
    if links_count >= 2 and len(text) >= 40:
        return True
    return False


def find_candidate_blocks(soup: BeautifulSoup) -> tuple[list[Tag], str, dict[str, int]]:
    pool = soup.find_all(["tr", "li", "div", "section", "article"])

    table_rows: list[Tag] = []
    list_items: list[Tag] = []
    card_blocks: list[Tag] = []

    for tag in pool:
        text = normalize_space(tag.get_text(" ", strip=True))
        links_count = len(tag.find_all("a", href=True))
        if not looks_result_like(text, links_count):
            continue

        if tag.name == "tr":
            table_rows.append(tag)
        elif tag.name == "li":
            list_items.append(tag)
        else:
            card_blocks.append(tag)

    sig_count = Counter(signature(tag) for tag in pool)
    repeated_cards = [tag for tag in card_blocks if sig_count[signature(tag)] >= 3]

    candidates = table_rows + list_items + repeated_cards
    structure_sizes = {
        "table": len(table_rows),
        "list": len(list_items),
        "card": len(repeated_cards),
    }

    nonzero = [name for name, count in structure_sizes.items() if count > 0]
    structure_guess = nonzero[0] if len(nonzero) == 1 else ("mixed" if nonzero else "unknown")

    return candidates, structure_guess, structure_sizes


def classify_links(block: Tag) -> tuple[str | None, str | None]:
    detail_url: str | None = None
    document_url: str | None = None

    for anchor in block.find_all("a", href=True):
        href = urljoin(BASE_URL, anchor.get("href", ""))
        href_l = href.lower()

        if document_url is None and any(h in href_l for h in DOC_HINTS):
            document_url = href
            continue

        if detail_url is None and any(h in href_l for h in DETAIL_HINTS):
            detail_url = href
            continue

        if detail_url is None:
            detail_url = href

    return detail_url, document_url


def extract_court(text: str) -> str | None:
    for pattern in COURT_PATTERNS:
        m = pattern.search(text)
        if m:
            return normalize_space(m.group(1))
    return None


def parse_item(block: Tag) -> dict[str, str | None]:
    raw_text = normalize_space(block.get_text(" ", strip=True))
    title = None

    title_tag = block.find(["h1", "h2", "h3", "h4", "strong", "b"]) or block.find("a")
    if title_tag:
        title_text = normalize_space(title_tag.get_text(" ", strip=True))
        title = title_text or None

    case_number = first_match(CASE_NUMBER_PATTERNS, raw_text)
    judgment_date = first_match(DATE_PATTERNS, raw_text)
    court = extract_court(raw_text)
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


def dedupe(items: list[dict[str, str | None]]) -> list[dict[str, str | None]]:
    seen: set[tuple[str | None, str | None, str | None]] = set()
    out: list[dict[str, str | None]] = []

    for item in items:
        key = (item.get("title"), item.get("case_number"), item.get("raw_text"))
        if key in seen:
            continue
        seen.add(key)
        out.append(item)

    return out


def build_report(
    structure_guess: str,
    structure_sizes: dict[str, int],
    candidate_blocks_count: int,
    items: list[dict[str, str | None]],
) -> str:
    case_hits = sum(1 for i in items if i.get("case_number"))
    date_hits = sum(1 for i in items if i.get("judgment_date"))
    detail_hits = sum(1 for i in items if i.get("detail_url"))

    lines = [
        "# Court requests replay result-list parser report (Day 8)",
        f"input_html: {INPUT_HTML_PATH}",
        f"output_json: {OUTPUT_JSON_PATH}",
        f"structure_guess: {structure_guess}",
        f"structure_sizes: {json.dumps(structure_sizes, ensure_ascii=False)}",
        "",
        f"total candidate blocks found: {candidate_blocks_count}",
        f"total result items extracted: {len(items)}",
        f"number of items with case number: {case_hits}",
        f"number of items with date: {date_hits}",
        f"number of items with detail link: {detail_hits}",
        "",
        "sample extracted items (first 5):",
    ]

    for idx, item in enumerate(items[:5], start=1):
        lines.append(f"- item {idx}: {json.dumps(item, ensure_ascii=False)}")

    if not items:
        lines.append("- (none)")

    lines.append("")
    lines.append("note: parser probe only; selector strategy should be refined with real replay snapshots.")
    return "\n".join(lines)


def run() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if BeautifulSoup is None:
        OUTPUT_JSON_PATH.write_text("[]\n", encoding="utf-8")
        OUTPUT_REPORT_PATH.write_text(
            "# Court requests replay result-list parser report (Day 8)\n"
            "error: missing dependency bs4 (BeautifulSoup).\n",
            encoding="utf-8",
        )
        print("total candidate blocks found: 0")
        print("total result items extracted: 0")
        print("structure guess (table/list/card/mixed): unknown")
        print("number of items with case number: 0")
        print("number of items with date: 0")
        print("number of items with detail link: 0")
        print("error: missing dependency bs4 (BeautifulSoup)")
        return 3

    if not INPUT_HTML_PATH.exists():
        OUTPUT_JSON_PATH.write_text("[]\n", encoding="utf-8")
        OUTPUT_REPORT_PATH.write_text(
            build_report("unknown", {"table": 0, "list": 0, "card": 0}, 0, [])
            + "\nerror: input html file not found.\n",
            encoding="utf-8",
        )
        print("total candidate blocks found: 0")
        print("total result items extracted: 0")
        print("structure guess (table/list/card/mixed): unknown")
        print("number of items with case number: 0")
        print("number of items with date: 0")
        print("number of items with detail link: 0")
        print(f"error: input html file not found at {INPUT_HTML_PATH}")
        return 1

    try:
        html = INPUT_HTML_PATH.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        html = INPUT_HTML_PATH.read_text(encoding="big5", errors="ignore")
    except OSError as exc:
        print("total candidate blocks found: 0")
        print("total result items extracted: 0")
        print("structure guess (table/list/card/mixed): unknown")
        print("number of items with case number: 0")
        print("number of items with date: 0")
        print("number of items with detail link: 0")
        print(f"error: failed reading input html: {exc}")
        return 2

    soup = BeautifulSoup(html, "html.parser")

    candidate_blocks, structure_guess, structure_sizes = find_candidate_blocks(soup)
    parsed_items = [parse_item(block) for block in candidate_blocks]
    parsed_items = [item for item in parsed_items if item.get("raw_text")]
    parsed_items = dedupe(parsed_items)

    OUTPUT_JSON_PATH.write_text(
        json.dumps(parsed_items, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    OUTPUT_REPORT_PATH.write_text(
        build_report(
            structure_guess=structure_guess,
            structure_sizes=structure_sizes,
            candidate_blocks_count=len(candidate_blocks),
            items=parsed_items,
        )
        + "\n",
        encoding="utf-8",
    )

    case_hits = sum(1 for i in parsed_items if i.get("case_number"))
    date_hits = sum(1 for i in parsed_items if i.get("judgment_date"))
    detail_hits = sum(1 for i in parsed_items if i.get("detail_url"))

    print(f"total candidate blocks found: {len(candidate_blocks)}")
    print(f"total result items extracted: {len(parsed_items)}")
    print(f"structure guess (table/list/card/mixed): {structure_guess}")
    print(f"number of items with case number: {case_hits}")
    print(f"number of items with date: {date_hits}")
    print(f"number of items with detail link: {detail_hits}")
    print(f"saved_json: {OUTPUT_JSON_PATH}")
    print(f"saved_report: {OUTPUT_REPORT_PATH}")
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
