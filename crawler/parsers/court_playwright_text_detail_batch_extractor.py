"""Day 13: Controlled batch TXT/fulltext detail extraction.

Scope constraints:
- input from refined result cards JSON only
- no pagination, no database writes
- prioritize direct sentence URL navigation
- keep fallback extraction path as backup
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
import sys
from typing import Any

if __package__ is None or __package__ == "":
    sys.path.append(str(Path(__file__).resolve().parents[2]))

from crawler.parsers.court_text_extraction_success import compute_extraction_success

PARSED_DIR = Path("data/parsed/court_probe")
INPUT_CARDS_PATH = PARSED_DIR / "playwright_result_cards_refined.json"
OUTPUT_BATCH_PATH = PARSED_DIR / "playwright_text_details_batch.jsonl"
OUTPUT_REPORT_PATH = PARSED_DIR / "playwright_text_details_batch_report.txt"

TARGET_MIN_BATCH = 20
TARGET_MAX_BATCH = 50
MIN_FULLTEXT_CHARS = 240
MIN_FULLTEXT_WORDS = 60

PLAYWRIGHT_ERROR = Exception


def load_playwright():
    try:
        from playwright.sync_api import Error as PlaywrightError  # type: ignore
        from playwright.sync_api import sync_playwright  # type: ignore
    except ModuleNotFoundError:
        return None, None
    return PlaywrightError, sync_playwright


def normalize_space(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def detect_language_from_url(url: str) -> str:
    lower = (url or "").lower()
    if "/zh/" in lower:
        return "zh"
    if "/pt/" in lower:
        return "pt"
    return "unknown"


def is_sentence_url(value: str) -> bool:
    return bool(re.match(r"^https?://[^\s]+/sentence/(zh|pt)/\d+/?$", value.strip(), flags=re.IGNORECASE))


def clean_full_text(text: str) -> str:
    lines = [normalize_space(line) for line in (text or "").splitlines()]
    lines = [line for line in lines if line]

    noisy_tokens = (
        "打印全文",
        "imprimir",
        "print",
        "返回",
        "voltar",
        "上一頁",
        "澳門特別行政區法院",
    )
    kept: list[str] = []
    for line in lines:
        lower = line.lower()
        if any(token in lower for token in noisy_tokens):
            continue
        kept.append(line)

    return normalize_space("\n".join(kept))


def good_full_text(text: str) -> bool:
    text = normalize_space(text)
    if not text:
        return False
    if len(text) < MIN_FULLTEXT_CHARS:
        return False
    if len(re.findall(r"\S+", text)) < MIN_FULLTEXT_WORDS:
        return False

    has_case_number = bool(re.search(r"\b\d{1,6}/\d{4}\b", text))
    has_date = bool(re.search(r"\b\d{1,2}/\d{1,2}/\d{4}\b", text))
    if has_case_number and has_date and len(text) < 420:
        return False

    return True


def extract_visible_main_text(page: "Page") -> str:
    script = r"""
    () => {
      const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
      const removeSelectors = [
        'script', 'style', 'noscript', 'header', 'footer', 'nav',
        '.navbar', '.menu', '.breadcrumb', '.breadcrumbs',
        '.fancybox-overlay', '.modal-backdrop'
      ];

      const bodyClone = document.body.cloneNode(true);
      for (const sel of removeSelectors) {
        for (const el of bodyClone.querySelectorAll(sel)) el.remove();
      }

      const candidates = [
        '#content', '.content', '.maincontent', 'main', 'article',
        '.sentence-content', '.judgment-content', '.detail', '.container'
      ];

      const blocks = [];
      for (const sel of candidates) {
        for (const el of bodyClone.querySelectorAll(sel)) {
          const txt = norm(el.innerText || el.textContent || '');
          if (txt.length >= 120) blocks.push(txt);
        }
      }

      if (blocks.length > 0) {
        blocks.sort((a, b) => b.length - a.length);
        return blocks[0];
      }

      const all = [];
      for (const el of bodyClone.querySelectorAll('h1,h2,h3,p,li,div,td,section')) {
        const txt = norm(el.innerText || el.textContent || '');
        if (txt.length >= 40) all.push(txt);
      }
      return norm(all.join('\n')) || norm(bodyClone.innerText || bodyClone.textContent || '');
    }
    """

    try:
        text = page.evaluate(script)
    except PLAYWRIGHT_ERROR:
        text = page.inner_text("body")
    return clean_full_text(text)


def extract_overlay_text(page: "Page") -> str:
    selectors = [".fancybox-inner", ".mfp-content", ".modal-body", ".ui-dialog-content", ".overlay-content"]
    for selector in selectors:
        try:
            loc = page.locator(selector)
            if loc.count() > 0 and loc.first.is_visible():
                text = clean_full_text(loc.first.inner_text(timeout=2500))
                if good_full_text(text):
                    return text
        except PLAYWRIGHT_ERROR:
            continue
    return ""


def try_direct_navigation(page: "Page", url: str) -> tuple[str, str]:
    page.goto(url, wait_until="domcontentloaded", timeout=45000)
    page.wait_for_timeout(1200)

    full_text = extract_visible_main_text(page)
    if good_full_text(full_text):
        return page.url, full_text

    overlay_text = extract_overlay_text(page)
    if good_full_text(overlay_text):
        return page.url, overlay_text

    raise RuntimeError("direct navigation loaded but did not produce valid full_text")


def fallback_modal_attempt(page: "Page", url: str) -> tuple[str, str]:
    page.goto(url, wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(1500)

    overlay_text = extract_overlay_text(page)
    if good_full_text(overlay_text):
        return page.url, overlay_text

    body_text = clean_full_text(page.inner_text("body"))
    if good_full_text(body_text):
        return page.url, body_text

    raise RuntimeError("fallback modal/overlay strategy failed")


def build_detail_record(card: dict[str, Any], source_url: str, full_text: str) -> dict[str, Any]:
    return {
        "case_number": card.get("case_number"),
        "decision_date": card.get("decision_date"),
        "language": detect_language_from_url(source_url),
        "title_or_issue": card.get("subject") or card.get("case_type"),
        "full_text": full_text,
        "source_type": "txt/fulltext",
        "extracted_from": source_url,
        "court": card.get("court") or "unknown",
    }


def choose_batch_candidates(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    resolved = [c for c in cards if isinstance(c.get("text_url_or_action"), str) and is_sentence_url(c["text_url_or_action"])]
    if len(resolved) >= TARGET_MIN_BATCH:
        return resolved[: min(TARGET_MAX_BATCH, len(resolved))]
    return resolved[: min(TARGET_MAX_BATCH, len(resolved))]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> int:
    if not INPUT_CARDS_PATH.exists():
        print(f"missing input file: {INPUT_CARDS_PATH}")
        return 1

    cards: list[dict[str, Any]] = json.loads(INPUT_CARDS_PATH.read_text(encoding="utf-8"))
    batch_cards = choose_batch_candidates(cards)
    attempted = len(batch_cards)

    success_count = 0
    failed_count = 0
    direct_opened_count = 0
    records: list[dict[str, Any]] = []
    failures: list[str] = []
    language_counts: Counter[str] = Counter()

    global PLAYWRIGHT_ERROR
    playwright_error, sync_playwright = load_playwright()
    if not sync_playwright:
        write_jsonl(OUTPUT_BATCH_PATH, [])
        appears_successful, failure_ratio = compute_extraction_success(
            attempted=attempted,
            successful=0,
            failed=attempted,
            non_empty_full_text_count=0,
        )
        avg_text_length = 0.0
        report_lines = [
            "# Day 13 controlled batch text-detail extraction report",
            f"input_cards_path: {INPUT_CARDS_PATH}",
            f"target batch range: {TARGET_MIN_BATCH}-{TARGET_MAX_BATCH}",
            f"resolved sentence URL candidates: {len([c for c in cards if isinstance(c.get('text_url_or_action'), str) and is_sentence_url(c['text_url_or_action'])])}",
            f"total records attempted: {attempted}",
            "total succeeded: 0",
            f"total failed: {attempted}",
            "non-empty full_text count: 0",
            f"failure ratio: {failure_ratio:.2%}",
            "zh count: 0",
            "pt count: 0",
            f"average text length: {avg_text_length:.2f}",
            "direct sentence pages opened count: 0",
            f"whether batch extraction appears successful: {appears_successful}",
            "",
            "failures:",
            "- Playwright is not installed in this environment.",
        ]
        OUTPUT_REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

        print(f"total records attempted: {attempted}")
        print("total succeeded: 0")
        print(f"total failed: {attempted}")
        print("zh count: 0")
        print("pt count: 0")
        print(f"average text length: {avg_text_length:.2f}")
        print(f"whether batch extraction appears successful: {appears_successful}")
        print("warning: Playwright is not installed in this environment.")
        return 0 if appears_successful else 2

    PLAYWRIGHT_ERROR = playwright_error

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="zh-HK")
        page = context.new_page()

        for idx, card in enumerate(batch_cards, start=1):
            url = card["text_url_or_action"]
            try:
                source_url, full_text = try_direct_navigation(page, url)
                direct_opened_count += 1
                record = build_detail_record(card, source_url, full_text)
                records.append(record)
                success_count += 1
                language_counts[record["language"]] += 1
                print(f"[{idx}] success via direct navigation: {url}")
            except Exception as direct_exc:
                print(f"[{idx}] direct navigation failed, trying fallback: {url} | {direct_exc}")
                try:
                    source_url, full_text = fallback_modal_attempt(page, url)
                    record = build_detail_record(card, source_url, full_text)
                    records.append(record)
                    success_count += 1
                    language_counts[record["language"]] += 1
                    print(f"[{idx}] success via fallback: {url}")
                except Exception as fallback_exc:
                    failed_count += 1
                    failures.append(f"{url} | direct={direct_exc} | fallback={fallback_exc}")
                    print(f"[{idx}] failed extraction: {url}")

        browser.close()

    write_jsonl(OUTPUT_BATCH_PATH, records)

    non_empty_full_text_count = sum(1 for row in records if normalize_space(row.get("full_text")))
    appears_successful, failure_ratio = compute_extraction_success(
        attempted=attempted,
        successful=success_count,
        failed=failed_count,
        non_empty_full_text_count=non_empty_full_text_count,
    )
    avg_text_length = (
        sum(len(normalize_space(row.get("full_text"))) for row in records) / len(records)
        if records
        else 0.0
    )

    report_lines = [
        "# Day 13 controlled batch text-detail extraction report",
        f"input_cards_path: {INPUT_CARDS_PATH}",
        f"target batch range: {TARGET_MIN_BATCH}-{TARGET_MAX_BATCH}",
        f"resolved sentence URL candidates: {len([c for c in cards if isinstance(c.get('text_url_or_action'), str) and is_sentence_url(c['text_url_or_action'])])}",
        f"total records attempted: {attempted}",
        f"total succeeded: {success_count}",
        f"total failed: {failed_count}",
        f"non-empty full_text count: {non_empty_full_text_count}",
        f"failure ratio: {failure_ratio:.2%}",
        f"zh count: {language_counts.get('zh', 0)}",
        f"pt count: {language_counts.get('pt', 0)}",
        f"average text length: {avg_text_length:.2f}",
        f"direct sentence pages opened count: {direct_opened_count}",
        f"whether batch extraction appears successful: {appears_successful}",
        "",
        "failures:",
        *([f"- {line}" for line in failures] or ["- none"]),
    ]
    OUTPUT_REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"total records attempted: {attempted}")
    print(f"total succeeded: {success_count}")
    print(f"total failed: {failed_count}")
    print(f"zh count: {language_counts.get('zh', 0)}")
    print(f"pt count: {language_counts.get('pt', 0)}")
    print(f"average text length: {avg_text_length:.2f}")
    print(f"whether batch extraction appears successful: {appears_successful}")

    return 0 if appears_successful else 2


if __name__ == "__main__":
    raise SystemExit(main())
