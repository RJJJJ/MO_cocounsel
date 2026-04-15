"""Day 10: Playwright-based extractor for Macau Courts judgment result cards.

Scope:
- open the judgment search page in a real browser
- submit one search (no pagination)
- extract repeated judgment cards from the rendered DOM
- persist artifacts + parsed JSON + report

Non-goals:
- no requests replay HTML dependency
- no detail-page parsing
- no DB integration
"""

from __future__ import annotations

import json
import re
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from playwright.sync_api import Page, TimeoutError, sync_playwright

TARGET_URL = "https://www.court.gov.mo/zh/subpage/researchjudgments"
BASE_URL = "https://www.court.gov.mo"

RAW_DIR = Path("data/raw/court_probe")
PARSED_DIR = Path("data/parsed/court_probe")
RESULT_HTML_PATH = RAW_DIR / "playwright_result_page.html"
RESULT_SCREENSHOT_PATH = RAW_DIR / "playwright_result_page.png"
OUTPUT_JSON_PATH = PARSED_DIR / "playwright_result_cards.json"
OUTPUT_REPORT_PATH = PARSED_DIR / "playwright_result_cards_report.txt"

DATE_RE = re.compile(r"(?:\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]\d{4}|\d{4}年\d{1,2}月\d{1,2}日)")
CASE_RE = re.compile(r"(?:\b[A-Z]{1,6}-?\d{1,6}/\d{2,4}\b|\b\d{1,6}/\d{2,4}\b|案(?:件)?(?:編號|號)?[:：\s]*[A-Za-z0-9\-/.]+)", re.IGNORECASE)

SUBJECT_KEYS = ("主題", "subject", "標的")
SUMMARY_KEYS = ("摘要", "sumário", "sumario", "summary")
DECISION_RESULT_KEYS = ("裁判結果", "決定", "resultado", "decision result")
REPORTING_JUDGE_KEYS = ("裁判書製作法官", "報告法官", "juiz relator", "reporting judge")
ASSISTANT_JUDGE_KEYS = ("助審法官", "adjuntos", "assistant judges")
TEXT_LINK_KEYS = ("全文", "text", "fulltext", "teor", "conteúdo", "conteudo")
PDF_LINK_KEYS = ("pdf", ".pdf")


def normalize_space(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def has_any(text: str, keys: tuple[str, ...]) -> bool:
    t = text.lower()
    return any(k.lower() in t for k in keys)


def infer_court(page_text: str, selected_court: str) -> str:
    if selected_court and selected_court != "全部":
        return selected_court
    if "中級法院" in page_text:
        return "中級法院"
    if "終審法院" in page_text:
        return "終審法院"
    if "初級法院" in page_text:
        return "初級法院"
    return "unknown"


def extract_field_by_label(text: str, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        pattern = re.compile(rf"{re.escape(key)}\s*[:：]?\s*([^\n\r]+)", re.IGNORECASE)
        m = pattern.search(text)
        if m:
            value = normalize_space(m.group(1))
            if value:
                return value
    return None


def fill_recent_30_days(page: Page) -> bool:
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    # 先用網站較可能接受的格式
    start_value = start_date.strftime("%d/%m/%Y")
    end_value = end_date.strftime("%d/%m/%Y")

    left = page.locator("#wizcasesearch_sentence_filter_type_decisionDate_left_date")
    right = page.locator("#wizcasesearch_sentence_filter_type_decisionDate_right_date")

    try:
        left.wait_for(timeout=5000)
        right.wait_for(timeout=5000)

        left.click()
        left.fill("")
        left.type(start_value, delay=30)

        right.click()
        right.fill("")
        right.type(end_value, delay=30)

        return True
    except Exception:
        return False


def try_select_intermediate_court(page: Page) -> str:
    sel = page.locator("#wizcasesearch_sentence_filter_type_court")
    try:
        sel.wait_for(timeout=5000)
        sel.select_option(label="中級法院")
        return "中級法院"
    except Exception:
        try:
            sel.select_option(label="所有")
            return "所有"
        except Exception:
            return "unknown"


def click_search(page: Page) -> bool:
    # 先鎖定裁判書搜尋主表單
    form = page.locator("form[action*='researchjudgments']").last

    try:
        form.wait_for(timeout=5000)
    except Exception:
        return False

    candidate_selectors = [
        "button[type='submit']",
        "input[type='submit']",
        "button:has-text('搜尋')",
        "input[value='搜尋']",
        "button",
        "input[type='button']",
    ]

    for selector in candidate_selectors:
        btn = form.locator(selector)
        if btn.count() == 0:
            continue
        for i in range(btn.count()):
            try:
                target = btn.nth(i)
                if target.is_visible():
                    target.scroll_into_view_if_needed()
                    target.click(timeout=5000, force=True)
                    return True
            except Exception:
                continue

    # 最後保底：直接提交 form
    try:
        form.evaluate("(f) => f.submit()")
        return True
    except Exception:
        return False


def wait_for_results_stable(page: Page) -> None:
    """Wait until rendered result-card count is stable."""
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
        const repeated = (sigMap.get(sig) || 0) >= 3;
        let score = 0;
        if (dateRe.test(txt)) score += 1;
        if (caseRe.test(txt)) score += 1;
        if (txt.includes('摘要') || txt.toLowerCase().includes('summary')) score += 1;
        if (txt.includes('主題') || txt.toLowerCase().includes('subject')) score += 1;
        if (txt.includes('裁判結果') || txt.toLowerCase().includes('resultado')) score += 1;
        const links = Array.from(el.querySelectorAll('a[href]')).map((a) => `${a.href} ${norm(a.innerText || '')}`.toLowerCase());
        if (links.some((x) => x.includes('pdf'))) score += 1;
        if (links.some((x) => x.includes('全文') || x.includes('text'))) score += 1;
        if (repeated && score >= 3) count += 1;
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
        page.wait_for_timeout(800)


def extract_card_blocks_from_dom(page: Page) -> list[dict[str, Any]]:
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
        if (!rawText || rawText.length < 40 || rawText.length > 3000) continue;

        const cls = norm(el.className || '').replace(/\s+/g, '.');
        const signature = `${el.tagName}|${cls}`;
        const repeatedCount = sigMap.get(signature) || 0;
        if (repeatedCount < 3) continue;

        const links = Array.from(el.querySelectorAll('a[href]')).map((a) => ({
        href: a.getAttribute('href') || '',
        text: norm(a.innerText || ''),
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

        out.push({
        signature,
        repeated_count: repeatedCount,
        score,
        raw_card_text: rawText,
        links,
        });
    }

    return out;
    }
    """
    return page.evaluate(script)


def parse_links(links: list[dict[str, str]]) -> tuple[str | None, str | None]:
    pdf_url = None
    text_url = None
    for link in links:
        href_raw = link.get("href") or ""
        href = urljoin(BASE_URL, href_raw)
        href_l = href.lower()
        label = normalize_space(link.get("text", "")).lower()

        if pdf_url is None and any(k in href_l or k in label for k in PDF_LINK_KEYS):
            pdf_url = href
            continue

        if text_url is None and any(k in href_l or k in label for k in TEXT_LINK_KEYS):
            text_url = href

    return pdf_url, text_url


def parse_card(card: dict[str, Any], court: str) -> dict[str, Any]:
    raw_text = normalize_space(card.get("raw_card_text", ""))
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
    pdf_url, text_url = parse_links(card.get("links", []))

    return {
        "court": court,
        "decision_date": decision_date_match.group(0) if decision_date_match else None,
        "case_number": case_number_match.group(0) if case_number_match else None,
        "case_type": case_type,
        "pdf_url": pdf_url,
        "text_url": text_url,
        "subject": subject,
        "summary": summary,
        "decision_result": decision_result,
        "reporting_judge": reporting_judge,
        "assistant_judges": assistant_judges,
        "raw_card_text": raw_text or None,
    }


def dedupe_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    out: list[dict[str, Any]] = []
    for card in cards:
        key = (card.get("decision_date"), card.get("case_number"), card.get("raw_card_text"))
        if key in seen:
            continue
        seen.add(key)
        out.append(card)
    return out


def hit_count(cards: list[dict[str, Any]], field: str) -> int:
    return sum(1 for c in cards if c.get(field))


def looks_like_true_judgment_cards(cards: list[dict[str, Any]]) -> bool:
    if not cards:
        return False
    case_ratio = hit_count(cards, "case_number") / len(cards)
    date_ratio = hit_count(cards, "decision_date") / len(cards)
    doc_ratio = sum(1 for c in cards if c.get("pdf_url") or c.get("text_url")) / len(cards)
    return case_ratio >= 0.6 and date_ratio >= 0.6 and doc_ratio >= 0.6


def build_report(total_detected: int, cards: list[dict[str, Any]], looks_true: bool, selected_court: str) -> str:
    fields = [
        "court",
        "decision_date",
        "case_number",
        "case_type",
        "pdf_url",
        "text_url",
        "subject",
        "summary",
        "decision_result",
        "reporting_judge",
        "assistant_judges",
        "raw_card_text",
    ]

    lines = [
        "# Court Playwright result-card extractor report (Day 10)",
        f"target_url: {TARGET_URL}",
        f"selected_court: {selected_court}",
        f"output_json: {OUTPUT_JSON_PATH}",
        f"snapshot_html: {RESULT_HTML_PATH}",
        "",
        f"total cards detected: {total_detected}",
        f"total cards parsed: {len(cards)}",
    ]
    for field in fields:
        lines.append(f"hit count - {field}: {hit_count(cards, field)}")

    signature_counter = Counter(c.get("raw_card_text", "")[:50] for c in cards if c.get("raw_card_text"))
    lines.extend(
        [
            "",
            f"looks_like_true_judgment_cards: {looks_true}",
            f"top raw-text prefixes: {signature_counter.most_common(3)}",
            "",
            "sample cards (first 3):",
        ]
    )

    for idx, card in enumerate(cards[:3], start=1):
        lines.append(f"\n## card {idx}")
        lines.append(json.dumps(card, ensure_ascii=False, indent=2))

    return "\n".join(lines) + "\n"

def wait_after_submit(page: Page) -> None:
    try:
        page.wait_for_url("**/subpage/searchresult**", timeout=15000)
        return
    except Exception:
        pass

    try:
        page.wait_for_load_state("domcontentloaded", timeout=10000)
    except Exception:
        pass

    page.wait_for_timeout(3000)

def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PARSED_DIR.mkdir(parents=True, exist_ok=True)

    selected_court = "全部"
    detected_cards: list[dict[str, Any]] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(locale="zh-HK")
            page = context.new_page()

            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=45_000)
            page.wait_for_timeout(2000)

            date_ok = fill_recent_30_days(page)
            selected_court = try_select_intermediate_court(page)

            if not date_ok:
                raise RuntimeError("failed to fill date inputs")

            if not click_search(page):
                raise RuntimeError("search submit failed: no search button clicked")

            wait_after_submit(page)

            RESULT_HTML_PATH.write_text(page.content(), encoding="utf-8")
            page.screenshot(path=str(RESULT_SCREENSHOT_PATH), full_page=True)
            detected_cards = extract_card_blocks_from_dom(page)

            browser.close()

    except Exception as exc:
        print("Playwright extractor failed.")
        print(f"error: {exc}")
        return 1

    page_text = RESULT_HTML_PATH.read_text(encoding="utf-8") if RESULT_HTML_PATH.exists() else ""
    court = infer_court(page_text, selected_court)

    parsed_cards = [parse_card(card, court=court) for card in detected_cards]
    parsed_cards = dedupe_cards(parsed_cards)
    looks_true = looks_like_true_judgment_cards(parsed_cards)

    OUTPUT_JSON_PATH.write_text(json.dumps(parsed_cards, ensure_ascii=False, indent=2), encoding="utf-8")
    OUTPUT_REPORT_PATH.write_text(
        build_report(
            total_detected=len(detected_cards),
            cards=parsed_cards,
            looks_true=looks_true,
            selected_court=selected_court,
        ),
        encoding="utf-8",
    )

    print(f"total cards detected: {len(detected_cards)}")
    print(f"total cards parsed: {len(parsed_cards)}")
    for field in ["decision_date", "case_number", "pdf_url", "text_url", "subject", "summary", "decision_result"]:
        print(f"hit count - {field}: {hit_count(parsed_cards, field)}")
    print(f"looks_like_true_judgment_cards: {looks_true}")
    print(f"selected_court: {selected_court}")
    print(f"output_json: {OUTPUT_JSON_PATH}")
    print(f"report_path: {OUTPUT_REPORT_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
