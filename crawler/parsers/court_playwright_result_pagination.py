"""Day 14: deterministic URL-based pagination over judgment result pages.

Scope:
- open paginated result URLs directly via known query parameters
- extract cards from each page via Playwright-rendered DOM
- aggregate + deduplicate cards across pages

Non-goals:
- no UI pagination-button discovery as primary path
- no detail-page extraction
- no batch fulltext extraction
- no DB integration
"""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urljoin


BASE_URL = "https://www.court.gov.mo"
RESULT_PATH = "/zh/subpage/researchjudgments"

PARSED_DIR = Path("data/parsed/court_probe")
OUTPUT_JSON_PATH = PARSED_DIR / "playwright_result_cards_paginated.json"
OUTPUT_REPORT_PATH = PARSED_DIR / "playwright_pagination_report.txt"

COURT_LABEL_MAP = {
    "tui": "終審法院",
    "tsi": "中級法院",
    "tjb": "初級法院",
    "ta": "行政法院",
    "all": "所有",
}

DATE_RE = re.compile(r"(?:\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]\d{4}|\d{4}年\d{1,2}月\d{1,2}日)")
CASE_RE = re.compile(r"(?:\b[A-Z]{1,6}-?\d{1,6}/\d{2,4}\b|\b\d{1,6}/\d{2,4}\b|案(?:件)?(?:編號|號)?[:：\s]*[A-Za-z0-9\-/.]+)", re.IGNORECASE)

SUBJECT_KEYS = ("主題", "subject", "標的")
SUMMARY_KEYS = ("摘要", "sumário", "sumario", "summary")
DECISION_RESULT_KEYS = ("裁判結果", "決定", "resultado", "decision result")
REPORTING_JUDGE_KEYS = ("裁判書製作法官", "報告法官", "juiz relator", "reporting judge")
ASSISTANT_JUDGE_KEYS = ("助審法官", "adjuntos", "assistant judges")
TEXT_LINK_KEYS = ("全文", "text", "fulltext", "teor", "conteúdo", "conteudo")
PDF_LINK_KEYS = ("pdf", ".pdf")


def load_playwright():
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ModuleNotFoundError:
        return None
    return sync_playwright


@dataclass
class PageAttempt:
    page_number: int
    url: str
    success: bool
    card_blocks: int
    parsed_cards: int
    error: str | None = None


def normalize_space(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def extract_field_by_label(text: str, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        m = re.search(rf"{re.escape(key)}\s*[:：]?\s*([^\n\r]+)", text, flags=re.IGNORECASE)
        if m:
            v = normalize_space(m.group(1))
            if v:
                return v
    return None


def build_result_url(court_code: str, page_number: int) -> str:
    query = {"court": court_code}
    if page_number > 1:
        query["page"] = str(page_number)
    return f"{BASE_URL}{RESULT_PATH}?{urlencode(query)}"


def wait_for_results_stable(page: "Page") -> None:
    script = r"""
    () => {
      const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
      const dateRe = /(?:\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]\d{4}|\d{4}年\d{1,2}月\d{1,2}日)/;
      const caseRe = /(?:\b[A-Z]{1,6}-?\d{1,6}\/\d{2,4}\b|\b\d{1,6}\/\d{2,4}\b|案(?:件)?(?:編號|號)?[:：\s]*[A-Za-z0-9\-/.]+)/i;
      const elems = Array.from(document.querySelectorAll('div,li,article,section,tr'));
      const sigMap = new Map();
      for (const el of elems) {
        const cls = norm(el.className || '').replace(/\s+/g, '.');
        const sig = `${el.tagName}|${cls}`;
        sigMap.set(sig, (sigMap.get(sig) || 0) + 1);
      }

      let count = 0;
      for (const el of elems) {
        const txt = norm(el.innerText || '');
        if (!txt || txt.length < 40) continue;
        const cls = norm(el.className || '').replace(/\s+/g, '.');
        const sig = `${el.tagName}|${cls}`;
        if ((sigMap.get(sig) || 0) < 3) continue;

        let score = 0;
        if (dateRe.test(txt)) score += 1;
        if (caseRe.test(txt)) score += 1;
        if (txt.includes('摘要') || txt.toLowerCase().includes('summary')) score += 1;
        if (txt.includes('主題') || txt.toLowerCase().includes('subject')) score += 1;

        const links = Array.from(el.querySelectorAll('a[href]')).map((a) => `${a.href} ${norm(a.innerText || '')}`.toLowerCase());
        if (links.some((x) => x.includes('pdf'))) score += 1;
        if (links.some((x) => x.includes('全文') || x.includes('text'))) score += 1;

        if (score >= 3) count += 1;
      }
      return count;
    }
    """

    stable_rounds = 0
    prev = -1
    for _ in range(20):
        current = int(page.evaluate(script))
        if current > 0 and current == prev:
            stable_rounds += 1
            if stable_rounds >= 3:
                return
        else:
            stable_rounds = 0
        prev = current
        page.wait_for_timeout(700)


def extract_card_blocks_from_dom(page: "Page") -> list[dict[str, Any]]:
    script = r"""
    () => {
      const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
      const dateRe = /(?:\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]\d{4}|\d{4}年\d{1,2}月\d{1,2}日)/;
      const caseRe = /(?:\b[A-Z]{1,6}-?\d{1,6}\/\d{2,4}\b|\b\d{1,6}\/\d{2,4}\b|案(?:件)?(?:編號|號)?[:：\s]*[A-Za-z0-9\-/.]+)/i;

      const elems = Array.from(document.querySelectorAll('div,li,article,section,tr'));
      const sigMap = new Map();
      for (const el of elems) {
        const cls = norm(el.className || '').replace(/\s+/g, '.');
        const sig = `${el.tagName}|${cls}`;
        sigMap.set(sig, (sigMap.get(sig) || 0) + 1);
      }

      const out = [];
      for (const el of elems) {
        const rawText = norm(el.innerText || '');
        if (!rawText || rawText.length < 40 || rawText.length > 4000) continue;

        const cls = norm(el.className || '').replace(/\s+/g, '.');
        const signature = `${el.tagName}|${cls}`;
        const repeatedCount = sigMap.get(signature) || 0;
        if (repeatedCount < 3) continue;

        const links = Array.from(el.querySelectorAll('a')).map((a) => ({
          href: a.getAttribute('href') || '',
          text: norm(a.innerText || ''),
          onclick: a.getAttribute('onclick') || ''
        }));

        let score = 0;
        if (dateRe.test(rawText)) score += 1;
        if (caseRe.test(rawText)) score += 1;
        if (rawText.includes('主題') || rawText.toLowerCase().includes('subject')) score += 1;
        if (rawText.includes('摘要') || rawText.toLowerCase().includes('summary')) score += 1;
        if (rawText.includes('裁判結果') || rawText.toLowerCase().includes('resultado')) score += 1;

        const flatLinks = links.map((l) => `${l.href} ${l.text}`.toLowerCase());
        if (flatLinks.some((v) => v.includes('pdf'))) score += 1;
        if (flatLinks.some((v) => v.includes('全文') || v.includes('text'))) score += 1;

        if (score < 3) continue;

        out.push({ raw_card_text: rawText, links, signature, repeated_count: repeatedCount, score });
      }
      return out;
    }
    """
    return page.evaluate(script)


def parse_links(links: list[dict[str, str]]) -> tuple[str | None, str | None]:
    pdf_url = None
    text_url_or_action = None

    for link in links:
        href_raw = (link.get("href") or "").strip()
        onclick_raw = normalize_space(link.get("onclick"))
        text = normalize_space(link.get("text"))

        href = urljoin(BASE_URL, href_raw) if href_raw and not href_raw.lower().startswith("javascript:") else href_raw
        href_l = (href or "").lower()
        text_l = text.lower()

        if pdf_url is None and any(k in href_l or k in text_l for k in PDF_LINK_KEYS):
            pdf_url = href if href else None
            continue

        if text_url_or_action is None and any(k in href_l or k in text_l for k in TEXT_LINK_KEYS):
            if href and not href.lower().startswith("javascript:"):
                text_url_or_action = href
            elif onclick_raw:
                text_url_or_action = f"action:{onclick_raw}"
            elif href:
                text_url_or_action = href

    return pdf_url, text_url_or_action


def parse_card(card: dict[str, Any], court_label: str, page_number: int) -> dict[str, Any]:
    raw_text = normalize_space(card.get("raw_card_text"))
    decision_date_match = DATE_RE.search(raw_text)
    case_number_match = CASE_RE.search(raw_text)

    case_type = None
    if case_number_match:
        suffix = normalize_space(raw_text[case_number_match.end() :])
        if suffix:
            case_type = suffix.split(" ")[0]

    subject = extract_field_by_label(raw_text, SUBJECT_KEYS)
    summary = extract_field_by_label(raw_text, SUMMARY_KEYS)
    decision_result = extract_field_by_label(raw_text, DECISION_RESULT_KEYS)
    reporting_judge = extract_field_by_label(raw_text, REPORTING_JUDGE_KEYS)
    assistant_judges = extract_field_by_label(raw_text, ASSISTANT_JUDGE_KEYS)
    pdf_url, text_url_or_action = parse_links(card.get("links", []))

    return {
        "court": court_label,
        "decision_date": decision_date_match.group(0) if decision_date_match else None,
        "case_number": case_number_match.group(0) if case_number_match else None,
        "case_type": case_type,
        "pdf_url": pdf_url,
        "text_url_or_action": text_url_or_action,
        "subject": subject,
        "summary": summary,
        "decision_result": decision_result,
        "reporting_judge": reporting_judge,
        "assistant_judges": assistant_judges,
        "raw_card_text": raw_text or None,
        "page_number": page_number,
    }


def dedupe_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    deduped: list[dict[str, Any]] = []

    for card in cards:
        doc_identity = card.get("pdf_url") or card.get("text_url_or_action")
        key = (
            card.get("court"),
            normalize_space(card.get("case_number")),
            normalize_space(card.get("decision_date")),
            normalize_space(doc_identity),
        )
        if not key[1] and not key[2] and not key[3]:
            key = (card.get("court"), None, None, normalize_space(card.get("raw_card_text")))

        if key in seen:
            continue
        seen.add(key)
        deduped.append(card)

    return deduped


def is_resolved_sentence_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    return bool(re.match(r"^https?://[^\s]+/sentence/(zh|pt)/\d+/?$", value.strip(), flags=re.IGNORECASE))


def parse_page(page: "Page", court_code: str, court_label: str, page_number: int) -> tuple[PageAttempt, list[dict[str, Any]]]:
    url = build_result_url(court_code, page_number)
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        page.wait_for_timeout(1200)
        wait_for_results_stable(page)
        blocks = extract_card_blocks_from_dom(page)
        cards = [parse_card(block, court_label=court_label, page_number=page_number) for block in blocks]
        return PageAttempt(page_number=page_number, url=url, success=True, card_blocks=len(blocks), parsed_cards=len(cards)), cards
    except Exception as exc:
        return (
            PageAttempt(page_number=page_number, url=url, success=False, card_blocks=0, parsed_cards=0, error=str(exc)),
            [],
        )


def build_report(court_code: str, attempts: list[PageAttempt], total_before: int, total_after: int, cards: list[dict[str, Any]]) -> str:
    pages_attempted = [a.page_number for a in attempts]
    pages_success = [a.page_number for a in attempts if a.success]
    resolved_count = sum(1 for c in cards if is_resolved_sentence_url(c.get("text_url_or_action")))
    pagination_success = len(pages_success) >= 2 and total_after > 0

    lines = [
        "# Day 14 deterministic pagination report",
        f"court code used: {court_code}",
        f"court label: {COURT_LABEL_MAP.get(court_code, 'unknown')}",
        f"pages attempted: {pages_attempted}",
        f"pages successfully parsed: {pages_success}",
        f"total cards before dedupe: {total_before}",
        f"total cards after dedupe: {total_after}",
        f"total resolved sentence URLs: {resolved_count}",
        f"pagination appears successful: {pagination_success}",
        f"output json: {OUTPUT_JSON_PATH}",
        "",
        "## page attempts",
    ]

    for a in attempts:
        lines.append(
            json.dumps(
                {
                    "page_number": a.page_number,
                    "url": a.url,
                    "success": a.success,
                    "card_blocks": a.card_blocks,
                    "parsed_cards": a.parsed_cards,
                    "error": a.error,
                },
                ensure_ascii=False,
            )
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic pagination extractor for court result cards.")
    parser.add_argument("--court", default="tsi", choices=sorted(COURT_LABEL_MAP.keys()), help="Court code, default tsi")
    parser.add_argument("--pages", type=int, default=3, help="Number of pages to attempt, default 3")
    args = parser.parse_args()

    PARSED_DIR.mkdir(parents=True, exist_ok=True)

    attempts: list[PageAttempt] = []
    all_cards: list[dict[str, Any]] = []
    court_label = COURT_LABEL_MAP.get(args.court, "unknown")

    sync_playwright = load_playwright()
    if not sync_playwright:
        deduped_cards: list[dict[str, Any]] = []
        for n in range(1, max(1, args.pages) + 1):
            attempts.append(
                PageAttempt(
                    page_number=n,
                    url=build_result_url(args.court, n),
                    success=False,
                    card_blocks=0,
                    parsed_cards=0,
                    error="playwright_not_installed",
                )
            )
    else:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(locale="zh-HK")
            page = context.new_page()

            for n in range(1, max(1, args.pages) + 1):
                attempt, cards = parse_page(page=page, court_code=args.court, court_label=court_label, page_number=n)
                attempts.append(attempt)
                all_cards.extend(cards)

            browser.close()

        deduped_cards = dedupe_cards(all_cards)

    OUTPUT_JSON_PATH.write_text(json.dumps(deduped_cards, ensure_ascii=False, indent=2), encoding="utf-8")
    OUTPUT_REPORT_PATH.write_text(
        build_report(
            court_code=args.court,
            attempts=attempts,
            total_before=len(all_cards),
            total_after=len(deduped_cards),
            cards=deduped_cards,
        ),
        encoding="utf-8",
    )

    pages_attempted = [a.page_number for a in attempts]
    pages_success = [a.page_number for a in attempts if a.success]
    resolved_count = sum(1 for c in deduped_cards if is_resolved_sentence_url(c.get("text_url_or_action")))
    pagination_success = len(pages_success) >= 2 and len(deduped_cards) > 0

    print(f"court code used: {args.court}")
    print(f"pages attempted: {pages_attempted}")
    print(f"pages successfully parsed: {pages_success}")
    print(f"total cards before dedupe: {len(all_cards)}")
    print(f"total cards after dedupe: {len(deduped_cards)}")
    print(f"total resolved sentence URLs: {resolved_count}")
    print(f"pagination appears successful: {pagination_success}")
    print(f"output json: {OUTPUT_JSON_PATH}")
    print(f"report path: {OUTPUT_REPORT_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
