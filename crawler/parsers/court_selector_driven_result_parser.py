"""Day 17: strict selector-driven parser for Macau Courts result cards.

Scope:
- Use Playwright with stateful search flow to open judgment results
- Parse pages 1, 2, 3 with confirmed DOM selectors
- Treat each ``li`` under ``div#zh-language-case.case_list`` as one card
- Exclude separator cards (class contains ``seperate``)
- Classify document links primarily by ``href`` patterns

Non-goals:
- No generic repeated-block scoring
- No fuzzy header parsing from raw block text
- No detail-page/batch fulltext extraction
- No database integration
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

BASE_URL = "https://www.court.gov.mo"
SEARCH_URL = f"{BASE_URL}/zh/subpage/researchjudgments"

PARSED_DIR = Path("data/parsed/court_probe")
OUTPUT_JSON_PATH = PARSED_DIR / "playwright_result_cards_selector_driven.json"
OUTPUT_REPORT_PATH = PARSED_DIR / "playwright_result_cards_selector_driven_report.txt"

RESULT_ROOT_SELECTOR = "div.maincontent div.case div#zh-language-case.case_list"
CARD_SELECTOR = "div#zh-language-case.case_list > li"


@dataclass
class ParseStats:
    pages_parsed: list[int]
    total_before_dedupe: int
    total_after_dedupe: int
    with_decision_date: int
    with_case_number: int
    with_case_type: int
    with_pdf_url: int
    with_text_url_or_action: int
    zh_text_links_count: int
    pt_text_links_count: int
    selector_successful: bool


def load_playwright():
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ModuleNotFoundError:
        return None
    return sync_playwright


def normalize_space(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def is_trivial_text(value: str) -> bool:
    text = normalize_space(value)
    if not text:
        return True
    return len(text) < 4


def set_page_param_from_result_url(result_url: str, page_number: int) -> str:
    parsed = urlparse(result_url)
    pairs = parse_qsl(parsed.query, keep_blank_values=True)

    out: list[tuple[str, str]] = []
    seen_page = False
    seen_court = False
    for key, val in pairs:
        if key == "page":
            if not seen_page:
                seen_page = True
                if page_number > 1:
                    out.append(("page", str(page_number)))
            continue
        out.append((key, val))
        if key == "court":
            seen_court = True

    if not seen_court:
        out.append(("court", "tsi"))
    if page_number > 1 and not seen_page:
        out.append(("page", str(page_number)))

    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(out), parsed.fragment))


def classify_document_links(links: list[dict[str, str]]) -> dict[str, Any]:
    zh_text_url: str | None = None
    pt_text_url: str | None = None
    zh_pdf: str | None = None
    pt_pdf: str | None = None
    other_pdf: str | None = None

    for link in links:
        href = normalize_space(link.get("href"))
        if not href:
            continue
        abs_url = urljoin(BASE_URL, href)
        href_lower = href.lower()

        is_pdf = href_lower.endswith(".pdf")
        if "/sentence/" in href_lower and is_pdf:
            if "/sentence/zh-" in href_lower:
                zh_pdf = abs_url
            elif "/sentence/pt-" in href_lower:
                pt_pdf = abs_url
            else:
                other_pdf = abs_url
            continue

        if "/sentence/zh/" in href_lower and not is_pdf:
            if not zh_text_url:
                zh_text_url = abs_url
            continue
        if "/sentence/pt/" in href_lower and not is_pdf:
            if not pt_text_url:
                pt_text_url = abs_url
            continue

        if is_pdf and not other_pdf:
            other_pdf = abs_url

    pdf_url = zh_pdf or pt_pdf or other_pdf
    text_url_or_action = zh_text_url or pt_text_url
    text_link_language = "zh" if zh_text_url else ("pt" if pt_text_url else None)

    return {
        "pdf_url": pdf_url,
        "text_url_or_action": text_url_or_action,
        "text_url_zh": zh_text_url,
        "text_url_pt": pt_text_url,
        "text_link_language": text_link_language,
    }


def parse_cards_from_current_page(page: "Page", page_number: int) -> list[dict[str, Any]]:
    page.wait_for_selector(RESULT_ROOT_SELECTOR, timeout=15000)

    script = r"""
    () => {
      const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
      const cards = [];
      const items = Array.from(document.querySelectorAll('div#zh-language-case.case_list > li'));

      for (const li of items) {
        const cls = norm(li.className || '');
        const rawText = norm(li.innerText || '');
        const links = Array.from(li.querySelectorAll('span.download a')).map((a) => ({
          href: a.getAttribute('href') || '',
          text: norm(a.innerText || ''),
        }));

        cards.push({
          class_name: cls,
          raw_card_text: rawText,
          decision_date: norm(li.querySelector('span.date')?.innerText || ''),
          case_number: norm(li.querySelector('span.num')?.innerText || ''),
          case_type: norm(li.querySelector('span.type')?.innerText || ''),
          links,
        });
      }

      return cards;
    }
    """
    raw_cards: list[dict[str, Any]] = page.evaluate(script)

    parsed_cards: list[dict[str, Any]] = []
    for raw in raw_cards:
        class_name = normalize_space(raw.get("class_name"))
        raw_card_text = normalize_space(raw.get("raw_card_text"))

        if "seperate" in class_name.lower():
            continue
        if is_trivial_text(raw_card_text):
            continue

        link_fields = classify_document_links(raw.get("links", []))

        parsed_cards.append(
            {
                "court": "中級法院",
                "decision_date": normalize_space(raw.get("decision_date")) or None,
                "case_number": normalize_space(raw.get("case_number")) or None,
                "case_type": normalize_space(raw.get("case_type")) or None,
                "pdf_url": link_fields["pdf_url"],
                "text_url_or_action": link_fields["text_url_or_action"],
                "text_url_zh": link_fields["text_url_zh"],
                "text_url_pt": link_fields["text_url_pt"],
                "text_link_language": link_fields["text_link_language"],
                "raw_card_text": raw_card_text,
                "page_number": page_number,
                # deferred fields from detail pages:
                "subject": None,
                "summary": None,
                "decision_result": None,
                "reporting_judge": None,
                "assistant_judges": None,
            }
        )

    return parsed_cards


def dedupe_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str, str, str]] = set()

    for card in cards:
        key = (
            normalize_space(card.get("court")) or "",
            normalize_space(card.get("case_number")) or "",
            normalize_space(card.get("decision_date")) or "",
            normalize_space(card.get("text_url_or_action") or card.get("pdf_url")) or "",
        )
        if key in seen:
            continue
        seen.add(key)
        deduped.append(card)

    return deduped


def gather_stats(cards_before: list[dict[str, Any]], cards_after: list[dict[str, Any]], pages_parsed: list[int]) -> ParseStats:
    with_decision_date = sum(1 for c in cards_after if c.get("decision_date"))
    with_case_number = sum(1 for c in cards_after if c.get("case_number"))
    with_case_type = sum(1 for c in cards_after if c.get("case_type"))
    with_pdf_url = sum(1 for c in cards_after if c.get("pdf_url"))
    with_text_url = sum(1 for c in cards_after if c.get("text_url_or_action"))
    zh_count = sum(1 for c in cards_after if c.get("text_url_zh"))
    pt_count = sum(1 for c in cards_after if c.get("text_url_pt"))

    selector_successful = (
        len(pages_parsed) == 3
        and len(cards_after) > 0
        and with_decision_date > 0
        and with_case_number > 0
        and with_case_type > 0
    )

    return ParseStats(
        pages_parsed=pages_parsed,
        total_before_dedupe=len(cards_before),
        total_after_dedupe=len(cards_after),
        with_decision_date=with_decision_date,
        with_case_number=with_case_number,
        with_case_type=with_case_type,
        with_pdf_url=with_pdf_url,
        with_text_url_or_action=with_text_url,
        zh_text_links_count=zh_count,
        pt_text_links_count=pt_count,
        selector_successful=selector_successful,
    )


def render_report(stats: ParseStats) -> str:
    lines = [
        "Day 17 selector-driven parser report",
        f"pages parsed: {stats.pages_parsed}",
        f"total cards before dedupe: {stats.total_before_dedupe}",
        f"total cards after dedupe: {stats.total_after_dedupe}",
        f"cards with decision_date: {stats.with_decision_date}",
        f"cards with case_number: {stats.with_case_number}",
        f"cards with case_type: {stats.with_case_type}",
        f"cards with pdf_url: {stats.with_pdf_url}",
        f"cards with text_url_or_action: {stats.with_text_url_or_action}",
        f"zh text links count: {stats.zh_text_links_count}",
        f"pt text links count: {stats.pt_text_links_count}",
        f"selector-driven parsing appears successful: {stats.selector_successful}",
    ]
    return "\n".join(lines) + "\n"


def run() -> int:
    sync_playwright = load_playwright()
    if sync_playwright is None:
        print("ERROR: playwright is not installed. Please install dependencies first.")
        return 2

    PARSED_DIR.mkdir(parents=True, exist_ok=True)

    cards_all_pages: list[dict[str, Any]] = []
    pages_parsed: list[int] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_selector("#wizcasesearch_sentence_filter_type_court", timeout=15000)
            page.select_option("#wizcasesearch_sentence_filter_type_court", label="中級法院")

            clicked = False
            for selector in [
                "form[action*='researchjudgments'] button[type='submit']",
                "form[action*='researchjudgments'] input[type='submit']",
                "form[action*='researchjudgments'] button:has-text('搜尋')",
            ]:
                target = page.locator(selector)
                if target.count() > 0:
                    target.first.click(timeout=10000)
                    clicked = True
                    break
            if not clicked:
                page.locator("form[action*='researchjudgments']").last.evaluate("f => f.submit()")

            page.wait_for_load_state("networkidle", timeout=20000)
            page.wait_for_selector(RESULT_ROOT_SELECTOR, timeout=15000)

            result_url = page.url

            for page_number in [1, 2, 3]:
                if page_number == 1:
                    current_url = result_url
                else:
                    current_url = set_page_param_from_result_url(result_url, page_number)
                    page.goto(current_url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_load_state("networkidle", timeout=20000)

                page_cards = parse_cards_from_current_page(page, page_number)
                if page_cards:
                    pages_parsed.append(page_number)
                    cards_all_pages.extend(page_cards)

            context.close()
            browser.close()

    except Exception as exc:
        print(f"ERROR: selector-driven parser failed: {exc}")
        return 1

    cards_deduped = dedupe_cards(cards_all_pages)
    stats = gather_stats(cards_all_pages, cards_deduped, pages_parsed)

    OUTPUT_JSON_PATH.write_text(json.dumps(cards_deduped, ensure_ascii=False, indent=2), encoding="utf-8")
    report_text = render_report(stats)
    OUTPUT_REPORT_PATH.write_text(report_text, encoding="utf-8")

    print(report_text, end="")
    print(f"JSON output: {OUTPUT_JSON_PATH}")
    print(f"Report output: {OUTPUT_REPORT_PATH}")
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
