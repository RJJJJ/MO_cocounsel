"""Day 12: Fix TXT/fulltext detail extraction via direct sentence URL navigation.

Scope constraints:
- input only from refined result cards JSON
- sample only first 1~3 cards with text_url_or_action
- primary path is direct page.goto(text_url_or_action)
- fallback to popup/modal/overlay extraction only when direct navigation fails
- no pagination, no batch job, no database writes
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any


PARSED_DIR = Path("data/parsed/court_probe")
INPUT_CARDS_PATH = PARSED_DIR / "playwright_result_cards_refined.json"
OUTPUT_SAMPLES_PATH = PARSED_DIR / "playwright_text_details_sample.json"
OUTPUT_REPORT_PATH = PARSED_DIR / "playwright_text_details_fix_report.txt"

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

    text_joined = "\n".join(kept)
    return normalize_space(text_joined)


def good_full_text(text: str) -> bool:
    text = normalize_space(text)
    if not text:
        return False

    if len(text) < MIN_FULLTEXT_CHARS:
        return False

    if len(re.findall(r"\S+", text)) < MIN_FULLTEXT_WORDS:
        return False

    # Avoid metadata-only strings: date + case number + tiny text.
    has_case_number = bool(re.search(r"\b\d{1,6}/\d{4}\b", text))
    has_date = bool(re.search(r"\b\d{1,2}/\d{1,2}/\d{4}\b", text))
    if has_case_number and has_date and len(text) < 420:
        return False

    return True


def extract_visible_main_text(page: "Page") -> str:
    script = r"""
    () => {
      const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
      const isVisible = (el) => {
        if (!el) return false;
        const style = window.getComputedStyle(el);
        if (!style) return false;
        if (style.visibility === 'hidden' || style.display === 'none') return false;
        if (style.opacity === '0') return false;
        const rect = el.getBoundingClientRect();
        return rect.width > 0 && rect.height > 0;
      };

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
        if (!isVisible(document.querySelector(el.tagName.toLowerCase()))) continue;
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
    selectors = [
        ".fancybox-inner",
        ".mfp-content",
        ".modal-body",
        ".ui-dialog-content",
        ".overlay-content",
    ]
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


def build_detail_sample(card: dict[str, Any], source_url: str, full_text: str) -> dict[str, Any]:
    return {
        "case_number": card.get("case_number"),
        "decision_date": card.get("decision_date"),
        "title_or_issue": card.get("subject") or card.get("case_type"),
        "full_text": full_text,
        "source_type": "txt/fulltext",
        "extracted_from": source_url,
        "language": detect_language_from_url(source_url),
    }


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
    # Fallback strategy only: retry with a fresh goto and prioritize known overlay containers.
    page.goto(url, wait_until="networkidle", timeout=45000)
    page.wait_for_timeout(1500)

    overlay_text = extract_overlay_text(page)
    if good_full_text(overlay_text):
        return page.url, overlay_text

    body_text = clean_full_text(page.inner_text("body"))
    if good_full_text(body_text):
        return page.url, body_text

    raise RuntimeError("fallback modal/overlay strategy failed")


def main() -> int:
    if not INPUT_CARDS_PATH.exists():
        print(f"missing input file: {INPUT_CARDS_PATH}")
        return 1

    cards: list[dict[str, Any]] = json.loads(INPUT_CARDS_PATH.read_text(encoding="utf-8"))

    candidates = [c for c in cards if isinstance(c.get("text_url_or_action"), str) and is_sentence_url(c["text_url_or_action"])]
    sample_cards = candidates[:3]

    attempted = len(sample_cards)
    success_count = 0
    failed_count = 0
    direct_opened_count = 0
    language_counts: Counter[str] = Counter()
    results: list[dict[str, Any]] = []
    failures: list[str] = []

    global PLAYWRIGHT_ERROR
    playwright_error, sync_playwright = load_playwright()
    if not sync_playwright:
        OUTPUT_SAMPLES_PATH.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT_SAMPLES_PATH.write_text(json.dumps([], ensure_ascii=False, indent=2), encoding="utf-8")
        report_lines = [
            "# Day 12 TXT/fulltext detail extraction fix report",
            f"input_cards_path: {INPUT_CARDS_PATH}",
            f"sample cards attempted: {attempted}",
            "successful text detail extractions: 0",
            f"failed detail extractions: {attempted}",
            "direct sentence pages opened count: 0",
            "language counts: {}",
            "whether text extraction now appears successful: False",
            "",
            "failures:",
            "- Playwright is not installed in this environment.",
        ]
        OUTPUT_REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
        print("sample cards attempted:", attempted)
        print("successful text detail extractions: 0")
        print("failed detail extractions:", attempted)
        print("direct sentence pages opened count: 0")
        print("language counts: {}")
        print("whether text extraction now appears successful: False")
        print("warning: Playwright is not installed in this environment.")
        return 2

    PLAYWRIGHT_ERROR = playwright_error

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="zh-HK")
        page = context.new_page()

        for idx, card in enumerate(sample_cards, start=1):
            text_url = card["text_url_or_action"]
            try:
                source_url, full_text = try_direct_navigation(page, text_url)
                direct_opened_count += 1
                sample = build_detail_sample(card, source_url, full_text)
                results.append(sample)
                success_count += 1
                language_counts[sample["language"]] += 1
                print(f"[{idx}] success via direct navigation: {text_url}")
            except Exception as direct_exc:
                print(f"[{idx}] direct navigation failed, trying fallback: {text_url} | {direct_exc}")
                try:
                    source_url, full_text = fallback_modal_attempt(page, text_url)
                    sample = build_detail_sample(card, source_url, full_text)
                    results.append(sample)
                    success_count += 1
                    language_counts[sample["language"]] += 1
                    print(f"[{idx}] success via fallback: {text_url}")
                except Exception as fallback_exc:
                    failed_count += 1
                    failures.append(f"{text_url} | direct={direct_exc} | fallback={fallback_exc}")
                    print(f"[{idx}] failed extraction: {text_url}")

        browser.close()

    OUTPUT_SAMPLES_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_SAMPLES_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    appears_successful = direct_opened_count >= 1 and success_count >= 1
    report_lines = [
        "# Day 12 TXT/fulltext detail extraction fix report",
        f"input_cards_path: {INPUT_CARDS_PATH}",
        f"sample cards attempted: {attempted}",
        f"successful text detail extractions: {success_count}",
        f"failed detail extractions: {failed_count}",
        f"direct sentence pages opened count: {direct_opened_count}",
        f"language counts: {dict(language_counts)}",
        f"whether text extraction now appears successful: {appears_successful}",
        "",
        "failures:",
        *([f"- {line}" for line in failures] or ["- none"]),
        "",
        "sample outputs:",
        json.dumps(results, ensure_ascii=False, indent=2),
    ]
    OUTPUT_REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"sample cards attempted: {attempted}")
    print(f"successful text detail extractions: {success_count}")
    print(f"failed detail extractions: {failed_count}")
    print(f"direct sentence pages opened count: {direct_opened_count}")
    print(f"language counts: {dict(language_counts)}")
    print(f"whether text extraction now appears successful: {appears_successful}")

    return 0 if appears_successful else 2


if __name__ == "__main__":
    raise SystemExit(main())
