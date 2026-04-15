#!/usr/bin/env python3
"""Day 24: add all-court crawling mode while preserving stable append-to-corpus pipeline."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

BASE_URL = "https://www.court.gov.mo"
SEARCH_URL = f"{BASE_URL}/zh/subpage/researchjudgments"

RESULT_ROOT_SELECTOR = "div.maincontent div.case div#zh-language-case.case_list"

CORPUS_ROOT = Path("data/corpus/raw/macau_court_cases")
CASES_ROOT = CORPUS_ROOT / "cases"
MANIFEST_PATH = CORPUS_ROOT / "manifest.jsonl"
REPORT_PATH = CORPUS_ROOT / "all_court_crawl_report.txt"

MIN_PAGE = 1
MAX_PAGE = 10
MIN_FULLTEXT_CHARS = 200

COURT_MODES = {"all", "tsi", "tui", "tjb", "ta"}


@dataclass
class CrawlStats:
    court_mode: str = "all"
    pages_attempted: int = 0
    valid_pages_parsed: int = 0
    cards_discovered: int = 0
    detail_pages_attempted: int = 0
    detail_pages_succeeded: int = 0
    duplicates_skipped: int = 0
    duplicates_skipped_by_text_url: int = 0
    duplicates_skipped_by_pdf_url: int = 0
    duplicates_skipped_by_fallback_metadata: int = 0
    cards_with_zh_text: int = 0
    cards_with_pt_text: int = 0
    cards_with_both_text_languages: int = 0
    cards_with_zh_pdf: int = 0
    cards_with_pt_pdf: int = 0
    cards_with_both_pdf_languages: int = 0
    new_corpus_records_added: int = 0
    stop_reason: str = ""


def load_playwright():
    try:
        from playwright.sync_api import Error as PlaywrightError  # type: ignore
        from playwright.sync_api import sync_playwright  # type: ignore
    except ModuleNotFoundError:
        return None, None
    return PlaywrightError, sync_playwright


def normalize_space(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalize_multiline_text(value: str | None) -> str:
    if not value:
        return ""
    text = value.replace("\r\n", "\n").replace("\r", "\n").replace("\u00a0", " ").replace("\ufeff", "")
    lines = [re.sub(r"[\t\f\v ]+", " ", line).strip() for line in text.split("\n")]
    out: list[str] = []
    blank_open = False
    for line in lines:
        if not line:
            if not blank_open:
                out.append("")
                blank_open = True
            continue
        blank_open = False
        out.append(line)
    return "\n".join(out).strip()


def extract_year(authoritative_decision_date: str, fallback_year: str = "unknown_year") -> str:
    if not authoritative_decision_date:
        return fallback_year
    m = re.search(r"(19|20)\d{2}", authoritative_decision_date)
    return m.group(0) if m else fallback_year


def slugify_case_number(case_number: str, index: int) -> str:
    cleaned = normalize_space(case_number).lower()
    cleaned = re.sub(r"[^0-9a-z]+", "_", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned or f"unknown_case_{index:04d}"


def ensure_unique_case_dir(base_dir: Path) -> Path:
    if not base_dir.exists():
        return base_dir
    suffix = 2
    while True:
        candidate = base_dir.parent / f"{base_dir.name}__dup{suffix}"
        if not candidate.exists():
            return candidate
        suffix += 1


def detect_language_from_url(url: str | None) -> str:
    lower = (url or "").lower()
    if "/zh/" in lower:
        return "zh"
    if "/pt/" in lower:
        return "pt"
    return "unknown"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Day 24 all-court crawling mode")
    parser.add_argument(
        "--court",
        default="all",
        choices=sorted(COURT_MODES),
        help="court mode: all (default) or single-court debug mode",
    )
    parser.add_argument("--start-page", type=int, default=MIN_PAGE)
    parser.add_argument("--end-page", type=int, default=MAX_PAGE)
    return parser.parse_args()


def set_page_and_court_params_from_result_url(result_url: str, page_number: int, court_mode: str) -> str:
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
        if key == "court":
            if not seen_court:
                out.append(("court", court_mode))
                seen_court = True
            continue
        out.append((key, val))

    if not seen_court:
        out.append(("court", court_mode))
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
            zh_text_url = zh_text_url or abs_url
            continue
        if "/sentence/pt/" in href_lower and not is_pdf:
            pt_text_url = pt_text_url or abs_url
            continue

        if is_pdf and not other_pdf:
            other_pdf = abs_url

    text_url_primary = zh_text_url or pt_text_url
    pdf_url_primary = zh_pdf or pt_pdf or other_pdf
    document_links: list[dict[str, str]] = []
    if zh_text_url:
        document_links.append({"kind": "text", "language": "zh", "url": zh_text_url})
    if pt_text_url:
        document_links.append({"kind": "text", "language": "pt", "url": pt_text_url})
    if zh_pdf:
        document_links.append({"kind": "pdf", "language": "zh", "url": zh_pdf})
    if pt_pdf:
        document_links.append({"kind": "pdf", "language": "pt", "url": pt_pdf})
    return {
        "pdf_url_primary": pdf_url_primary,
        "pdf_url_zh": zh_pdf,
        "pdf_url_pt": pt_pdf,
        "pdf_url": pdf_url_primary,
        "text_url_primary": text_url_primary,
        "text_url_zh": zh_text_url,
        "text_url_pt": pt_text_url,
        "text_url_or_action": text_url_primary,
        "document_links": document_links,
    }


def parse_cards_from_current_page(page: "Page", page_number: int) -> list[dict[str, Any]]:
    page.wait_for_selector(RESULT_ROOT_SELECTOR, timeout=15_000)
    raw_cards: list[dict[str, Any]] = page.evaluate(
        r"""
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
    )

    parsed: list[dict[str, Any]] = []
    for raw in raw_cards:
        class_name = normalize_space(raw.get("class_name")).lower()
        raw_card_text = normalize_space(raw.get("raw_card_text"))
        if "seperate" in class_name or len(raw_card_text) < 4:
            continue

        link_fields = classify_document_links(raw.get("links", []))
        parsed.append(
            {
                "court": "澳門法院",
                "source_list_case_number": normalize_space(raw.get("case_number")) or None,
                "source_list_decision_date": normalize_space(raw.get("decision_date")) or None,
                "source_list_case_type": normalize_space(raw.get("case_type")) or None,
                "pdf_url": link_fields["pdf_url"],
                "pdf_url_primary": link_fields["pdf_url_primary"],
                "pdf_url_zh": link_fields["pdf_url_zh"],
                "pdf_url_pt": link_fields["pdf_url_pt"],
                "text_url_primary": link_fields["text_url_primary"],
                "text_url_zh": link_fields["text_url_zh"],
                "text_url_pt": link_fields["text_url_pt"],
                "text_url_or_action": link_fields["text_url_or_action"],
                "document_links": link_fields["document_links"],
                "page_number": page_number,
            }
        )
    return parsed


def extract_body_first_text(page: "Page", playwright_error: type[Exception]) -> str:
    script = r"""
    () => {
      const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
      const body = document.body;
      if (!body) return '';
      const clone = body.cloneNode(true);
      for (const sel of ['script', 'style', 'noscript']) {
        for (const el of clone.querySelectorAll(sel)) el.remove();
      }
      const allNodes = Array.from(clone.querySelectorAll('*'));
      for (const el of allNodes) {
        const text = norm(el.textContent || '');
        const style = ((el.getAttribute('style') || '') + ' ' + (el.style?.cssText || '')).toLowerCase();
        const onclick = (el.getAttribute('onclick') || '').toLowerCase();
        const tag = (el.tagName || '').toLowerCase();
        const hasPrintText = text.includes('打印全文') || text.includes('列印全文') || text.toLowerCase()==='print' || text.toLowerCase().includes('imprimir');
        const printLike = onclick.includes('window.print') || style.includes('float: right');
        if (hasPrintText && (printLike || tag === 'a' || tag === 'div')) {
          el.remove();
          continue;
        }
        if (tag === 'a' && (onclick.includes('window.print') || hasPrintText)) {
          el.remove();
        }
      }
      return (clone.innerText || clone.textContent || '').trim();
    }
    """
    try:
        return str(page.evaluate(script) or "")
    except playwright_error:
        return page.inner_text("body")


def remove_print_noise_from_text(text: str) -> str:
    patterns = [
        re.compile(r"^打印全文$", flags=re.IGNORECASE),
        re.compile(r"^列印全文$", flags=re.IGNORECASE),
        re.compile(r"^print$", flags=re.IGNORECASE),
        re.compile(r"^imprimir(?:\s+texto\s+integral)?$", flags=re.IGNORECASE),
    ]
    lines: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped and any(p.match(stripped) for p in patterns):
            continue
        lines.append(line)
    return "\n".join(lines)


def good_full_text(text: str) -> bool:
    text = text.strip()
    return bool(text and len(text) >= MIN_FULLTEXT_CHARS and len(re.findall(r"\S+", text)) >= 60)


def read_manifest(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    if not path.exists():
        return records
    with path.open("r", encoding="utf-8") as infile:
        for line_no, line in enumerate(infile, start=1):
            raw = line.strip()
            if not raw:
                continue
            try:
                obj = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSON at line {line_no} in {path}: {exc}") from exc
            if isinstance(obj, dict):
                records.append(obj)
    return records


def normalize_source_identity_url(value: Any) -> str:
    raw = normalize_space(value)
    if not raw:
        return ""
    parsed = urlparse(raw)
    scheme = (parsed.scheme or "https").lower()
    netloc = parsed.netloc.lower()
    path = parsed.path or "/"
    if path != "/":
        path = path.rstrip("/")
    query_items = parse_qsl(parsed.query, keep_blank_values=True)
    normalized_query = urlencode(sorted(query_items))
    return urlunparse((scheme, netloc, path, parsed.params, normalized_query, ""))


def collect_document_urls(record: dict[str, Any], *, kind: str) -> list[str]:
    urls: set[str] = set()
    for entry in record.get("document_links") or []:
        if not isinstance(entry, dict):
            continue
        if normalize_space(entry.get("kind")).lower() != kind:
            continue
        normalized = normalize_source_identity_url(entry.get("url"))
        if normalized:
            urls.add(normalized)

    if kind == "text":
        fallback_candidates = [
            record.get("text_url_primary"),
            record.get("text_url_zh"),
            record.get("text_url_pt"),
            record.get("text_url_or_action"),
        ]
    else:
        fallback_candidates = [
            record.get("pdf_url_primary"),
            record.get("pdf_url_zh"),
            record.get("pdf_url_pt"),
            record.get("pdf_url"),
        ]

    for candidate in fallback_candidates:
        normalized = normalize_source_identity_url(candidate)
        if normalized:
            urls.add(normalized)

    return sorted(urls)


def get_authoritative_case_number(record: dict[str, Any]) -> str:
    return normalize_space(record.get("authoritative_case_number") or record.get("source_list_case_number"))


def get_authoritative_decision_date(record: dict[str, Any]) -> str:
    return normalize_space(record.get("authoritative_decision_date") or record.get("source_list_decision_date"))


def build_fallback_metadata_key(record: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        normalize_space(record.get("court")).lower(),
        get_authoritative_case_number(record).lower(),
        get_authoritative_decision_date(record).lower(),
        normalize_space(record.get("language")).lower(),
    )


def build_duplicate_key(record: dict[str, Any]) -> tuple[str, str]:
    text_urls = collect_document_urls(record, kind="text")
    if text_urls:
        return ("text_url", "|".join(text_urls))
    pdf_urls = collect_document_urls(record, kind="pdf")
    if pdf_urls:
        return ("pdf_url", "|".join(pdf_urls))
    return ("fallback_metadata", "|".join(build_fallback_metadata_key(record)))


def append_record_to_corpus(record: dict[str, Any], manifest_fh, new_index: int) -> None:
    language = normalize_space(record.get("language")) or "unknown"
    authoritative_case_number = get_authoritative_case_number(record)
    authoritative_decision_date = get_authoritative_decision_date(record)
    case_slug = slugify_case_number(authoritative_case_number, new_index)
    year = extract_year(authoritative_decision_date)

    case_dir = ensure_unique_case_dir(CASES_ROOT / language / year / case_slug)
    case_dir.mkdir(parents=True, exist_ok=True)

    metadata_path = case_dir / "metadata.json"
    full_text_path = case_dir / "full_text.txt"
    full_text = normalize_space(record.get("full_text"))
    full_text_path.write_text(full_text, encoding="utf-8")

    relative_full_text_path = full_text_path.relative_to(CORPUS_ROOT).as_posix()
    relative_metadata_path = metadata_path.relative_to(CORPUS_ROOT).as_posix()

    metadata = {
        "court": normalize_space(record.get("court")),
        "source_list_case_number": authoritative_case_number,
        "source_list_decision_date": authoritative_decision_date,
        "source_list_case_type": normalize_space(record.get("source_list_case_type")),
        "language": language,
        "pdf_url": normalize_space(record.get("pdf_url")),
        "pdf_url_primary": normalize_space(record.get("pdf_url_primary") or record.get("pdf_url")),
        "pdf_url_zh": normalize_space(record.get("pdf_url_zh")),
        "pdf_url_pt": normalize_space(record.get("pdf_url_pt")),
        "text_url_or_action": normalize_space(record.get("text_url_or_action")),
        "text_url_primary": normalize_space(record.get("text_url_primary") or record.get("text_url_or_action")),
        "text_url_zh": normalize_space(record.get("text_url_zh")),
        "text_url_pt": normalize_space(record.get("text_url_pt")),
        "document_links": record.get("document_links") or [],
        "page_number": record.get("page_number"),
        "extraction_source": "day24_all_court_crawling_mode",
        "full_text_path": relative_full_text_path,
    }
    metadata_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    manifest_record = {
        "language": language,
        "authoritative_case_number": authoritative_case_number,
        "authoritative_decision_date": authoritative_decision_date,
        "court": metadata["court"],
        "pdf_url": metadata["pdf_url"],
        "pdf_url_primary": metadata["pdf_url_primary"],
        "pdf_url_zh": metadata["pdf_url_zh"],
        "pdf_url_pt": metadata["pdf_url_pt"],
        "text_url_or_action": metadata["text_url_or_action"],
        "text_url_primary": metadata["text_url_primary"],
        "text_url_zh": metadata["text_url_zh"],
        "text_url_pt": metadata["text_url_pt"],
        "document_links": metadata["document_links"],
        "metadata_path": relative_metadata_path,
        "full_text_path": relative_full_text_path,
    }
    manifest_fh.write(json.dumps(manifest_record, ensure_ascii=False) + "\n")


def write_report(stats: CrawlStats) -> None:
    appears_successful = stats.new_corpus_records_added > 0 or stats.duplicates_skipped > 0
    lines = [
        "Day 24 all-court crawling mode report",
        "====================================",
        f"court mode used: {stats.court_mode}",
        f"pages attempted: {stats.pages_attempted}",
        f"valid pages parsed: {stats.valid_pages_parsed}",
        f"cards discovered: {stats.cards_discovered}",
        f"detail pages attempted: {stats.detail_pages_attempted}",
        f"detail pages succeeded: {stats.detail_pages_succeeded}",
        "duplicate strategy used: sorted all text URLs -> sorted all pdf URLs -> (court, authoritative_case_number, authoritative_decision_date, language)",
        f"duplicates skipped: {stats.duplicates_skipped}",
        f"duplicates skipped by text_url: {stats.duplicates_skipped_by_text_url}",
        f"duplicates skipped by pdf_url: {stats.duplicates_skipped_by_pdf_url}",
        f"duplicates skipped by fallback metadata key: {stats.duplicates_skipped_by_fallback_metadata}",
        f"cards with zh text: {stats.cards_with_zh_text}",
        f"cards with pt text: {stats.cards_with_pt_text}",
        f"cards with both text languages: {stats.cards_with_both_text_languages}",
        f"cards with zh pdf: {stats.cards_with_zh_pdf}",
        f"cards with pt pdf: {stats.cards_with_pt_pdf}",
        f"cards with both pdf languages: {stats.cards_with_both_pdf_languages}",
        f"new corpus records added: {stats.new_corpus_records_added}",
        f"stop reason: {stats.stop_reason or 'none'}",
        f"whether all-court crawling appears successful: {'yes' if appears_successful else 'no'}",
    ]
    REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def print_summary(stats: CrawlStats) -> None:
    appears_successful = stats.new_corpus_records_added > 0 or stats.duplicates_skipped > 0
    print(f"court mode used: {stats.court_mode}")
    print(f"pages attempted: {stats.pages_attempted}")
    print(f"valid pages parsed: {stats.valid_pages_parsed}")
    print(f"cards discovered: {stats.cards_discovered}")
    print(f"detail pages attempted: {stats.detail_pages_attempted}")
    print(f"detail pages succeeded: {stats.detail_pages_succeeded}")
    print("duplicate strategy used: sorted all text URLs -> sorted all pdf URLs -> fallback metadata key")
    print(f"duplicates skipped: {stats.duplicates_skipped}")
    print(f"duplicates skipped by text_url: {stats.duplicates_skipped_by_text_url}")
    print(f"duplicates skipped by pdf_url: {stats.duplicates_skipped_by_pdf_url}")
    print(f"duplicates skipped by fallback metadata key: {stats.duplicates_skipped_by_fallback_metadata}")
    print(f"cards with zh text: {stats.cards_with_zh_text}")
    print(f"cards with pt text: {stats.cards_with_pt_text}")
    print(f"cards with both text languages: {stats.cards_with_both_text_languages}")
    print(f"cards with zh pdf: {stats.cards_with_zh_pdf}")
    print(f"cards with pt pdf: {stats.cards_with_pt_pdf}")
    print(f"cards with both pdf languages: {stats.cards_with_both_pdf_languages}")
    print(f"new corpus records added: {stats.new_corpus_records_added}")
    print(f"whether all-court crawling appears successful: {'yes' if appears_successful else 'no'}")


def run() -> int:
    args = parse_args()
    start_page = max(MIN_PAGE, args.start_page)
    end_page = max(start_page, args.end_page)

    playwright_error, sync_playwright = load_playwright()
    stats = CrawlStats(court_mode=args.court)

    if not sync_playwright:
        stats.stop_reason = "playwright is not installed"
        write_report(stats)
        print("[ERROR] playwright is not installed")
        print_summary(stats)
        print(f"report path: {REPORT_PATH}")
        return 2

    CORPUS_ROOT.mkdir(parents=True, exist_ok=True)
    CASES_ROOT.mkdir(parents=True, exist_ok=True)

    manifest_rows = read_manifest(MANIFEST_PATH)
    seen_keys = {build_duplicate_key(r) for r in manifest_rows}
    seen_page_signatures: set[tuple[tuple[str, ...], ...]] = set()

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(locale="zh-HK")
            page = context.new_page()

            page.goto(SEARCH_URL, wait_until="domcontentloaded", timeout=45_000)
            page.wait_for_selector("#wizcasesearch_sentence_filter_type_court", timeout=15_000)
            page.select_option("#wizcasesearch_sentence_filter_type_court", value=args.court)

            clicked = False
            for selector in [
                "form[action*='researchjudgments'] button[type='submit']",
                "form[action*='researchjudgments'] input[type='submit']",
                "form[action*='researchjudgments'] button:has-text('搜尋')",
            ]:
                target = page.locator(selector)
                if target.count() > 0:
                    target.first.click(timeout=10_000)
                    clicked = True
                    break
            if not clicked:
                page.locator("form[action*='researchjudgments']").last.evaluate("f => f.submit()")

            page.wait_for_load_state("networkidle", timeout=20_000)
            page.wait_for_selector(RESULT_ROOT_SELECTOR, timeout=15_000)
            submitted_result_url = page.url

            detail_page = context.new_page()

            with MANIFEST_PATH.open("a", encoding="utf-8") as manifest_fh:
                new_index = len(manifest_rows) + 1

                for page_number in range(start_page, end_page + 1):
                    stats.pages_attempted += 1

                    if page_number == start_page:
                        target_url = set_page_and_court_params_from_result_url(submitted_result_url, page_number, args.court)
                    else:
                        target_url = set_page_and_court_params_from_result_url(submitted_result_url, page_number, args.court)
                    page.goto(target_url, wait_until="domcontentloaded", timeout=45_000)
                    page.wait_for_load_state("networkidle", timeout=20_000)

                    page_cards = parse_cards_from_current_page(page, page_number)
                    if not page_cards:
                        stats.stop_reason = f"invalid/no-result page at page {page_number}"
                        break

                    signature = tuple(
                        sorted(
                            (
                                normalize_space(c.get("source_list_case_number")),
                                normalize_space(c.get("source_list_decision_date")),
                                "|".join(collect_document_urls(c, kind="text")) or "|".join(collect_document_urls(c, kind="pdf")),
                            )
                            for c in page_cards
                        )
                    )
                    if signature in seen_page_signatures:
                        stats.stop_reason = f"duplicate result page signature detected at page {page_number}"
                        break
                    seen_page_signatures.add(signature)

                    stats.valid_pages_parsed += 1
                    stats.cards_discovered += len(page_cards)
                    stats.cards_with_zh_text += sum(1 for c in page_cards if normalize_space(c.get("text_url_zh")))
                    stats.cards_with_pt_text += sum(1 for c in page_cards if normalize_space(c.get("text_url_pt")))
                    stats.cards_with_both_text_languages += sum(
                        1 for c in page_cards if normalize_space(c.get("text_url_zh")) and normalize_space(c.get("text_url_pt"))
                    )
                    stats.cards_with_zh_pdf += sum(1 for c in page_cards if normalize_space(c.get("pdf_url_zh")))
                    stats.cards_with_pt_pdf += sum(1 for c in page_cards if normalize_space(c.get("pdf_url_pt")))
                    stats.cards_with_both_pdf_languages += sum(
                        1 for c in page_cards if normalize_space(c.get("pdf_url_zh")) and normalize_space(c.get("pdf_url_pt"))
                    )

                    for card in page_cards:
                        detail_url = normalize_space(card.get("text_url_primary") or card.get("text_url_or_action"))
                        if not detail_url:
                            continue

                        stats.detail_pages_attempted += 1
                        try:
                            detail_page.goto(detail_url, wait_until="domcontentloaded", timeout=45_000)
                            detail_page.wait_for_load_state("networkidle", timeout=20_000)
                            raw_text = extract_body_first_text(detail_page, playwright_error)
                            cleaned_text = normalize_multiline_text(remove_print_noise_from_text(raw_text))
                        except Exception:
                            continue

                        if not good_full_text(cleaned_text):
                            continue

                        stats.detail_pages_succeeded += 1

                        record = {
                            **card,
                            "language": detect_language_from_url(detail_url),
                            "full_text": cleaned_text,
                        }

                        duplicate_key = build_duplicate_key(record)

                        if duplicate_key in seen_keys:
                            stats.duplicates_skipped += 1
                            if duplicate_key[0] == "text_url":
                                stats.duplicates_skipped_by_text_url += 1
                            elif duplicate_key[0] == "pdf_url":
                                stats.duplicates_skipped_by_pdf_url += 1
                            else:
                                stats.duplicates_skipped_by_fallback_metadata += 1
                            continue

                        append_record_to_corpus(record, manifest_fh, new_index=new_index)
                        new_index += 1
                        stats.new_corpus_records_added += 1
                        seen_keys.add(duplicate_key)

                if not stats.stop_reason and stats.pages_attempted >= (end_page - start_page + 1):
                    stats.stop_reason = f"reached configured page range {start_page}..{end_page}"

            context.close()
            browser.close()

        write_report(stats)
        print_summary(stats)
        print(f"report path: {REPORT_PATH}")
        return 0

    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        write_report(stats)
        print_summary(stats)
        print(f"report path: {REPORT_PATH}")
        return 1


def main() -> int:
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
