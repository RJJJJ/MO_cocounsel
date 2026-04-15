"""Day 16A: fix paginated result-card boundary segmentation.

Scope:
- reuse Day 14/15 stateful pagination flow
- parse pages 1..N (default 3)
- segment one DOM card container -> one extracted judgment record
- preserve PDF + text/fulltext links and core card fields

Non-goals:
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
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse

BASE_URL = "https://www.court.gov.mo"
RESULT_PATH = "/zh/subpage/researchjudgments"

PARSED_DIR = Path("data/parsed/court_probe")
OUTPUT_JSON_PATH = PARSED_DIR / "playwright_result_cards_paginated_clean.json"
OUTPUT_REPORT_PATH = PARSED_DIR / "playwright_result_card_boundary_fix_report.txt"

COURT_LABEL_MAP = {
    "tui": "終審法院",
    "tsi": "中級法院",
    "tjb": "初級法院",
    "ta": "行政法院",
    "all": "所有",
}

DATE_RE = re.compile(r"(?:\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]\d{4}|\d{4}年\d{1,2}月\d{1,2}日)")
CASE_NUMBER_RE = re.compile(r"\b\d{1,6}/\d{4}\b")
CASE_WITH_PREFIX_RE = re.compile(r"\b[A-Z]{1,8}-?\d{1,6}/\d{2,4}\b", re.IGNORECASE)

SUBJECT_KEYS = ("主題", "subject", "標的")
SUMMARY_KEYS = ("摘要", "sumário", "sumario", "summary")
DECISION_RESULT_KEYS = ("裁判結果", "決定", "resultado", "decision result")
REPORTING_JUDGE_KEYS = ("裁判書製作法官", "報告法官", "juiz relator", "reporting judge")
ASSISTANT_JUDGE_KEYS = ("助審法官", "adjuntos", "assistant judges")

PDF_HINTS = ("pdf", ".pdf", "判決書")
TEXT_HINTS = ("全文", "text", "fulltext", "full text", "teor", "conteúdo", "conteudo", "sentença", "sentenca", "sentence", "裁判書")
ZH_SENTENCE_RE = re.compile(r"/sentence/zh/\d+/?", re.IGNORECASE)
PT_SENTENCE_RE = re.compile(r"/sentence/pt/\d+/?", re.IGNORECASE)


@dataclass
class PageAttempt:
    page_number: int
    url: str
    success: bool
    card_blocks: int
    parsed_cards: int
    cards_with_case_number: int
    cards_with_doc_links: int
    valid_result_page: bool
    invalid_reason: str | None = None
    error: str | None = None


def load_playwright():
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except ModuleNotFoundError:
        return None
    return sync_playwright


def normalize_space(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def normalize_url_or_action(value: str | None) -> str | None:
    v = normalize_space(value)
    if not v:
        return None
    if v.lower().startswith("javascript:"):
        return f"action:{v}"
    if v.startswith("action:"):
        return v
    if "://" in v or v.startswith("/"):
        return urljoin(BASE_URL, v)
    return v


def cleanup_case_type(value: str | None) -> str | None:
    v = normalize_space(value)
    if not v:
        return None
    if re.fullmatch(r"/\d{2,4}", v):
        return None
    v = re.sub(r"^[\-:：,，.]+", "", v)
    v = normalize_space(v)
    if not v or re.fullmatch(r"/\d{2,4}", v):
        return None
    return v


def extract_labeled_field(lines: list[str], keys: tuple[str, ...]) -> str | None:
    for line in lines:
        for key in keys:
            m = re.search(rf"{re.escape(key)}\s*[:：]?\s*(.+)$", line, flags=re.IGNORECASE)
            if not m:
                continue
            value = normalize_space(m.group(1))
            if value:
                return value
    return None


def parse_case_number_and_type(lines: list[str], full_text: str) -> tuple[str | None, str | None]:
    for line in lines:
        number = CASE_NUMBER_RE.search(line) or CASE_WITH_PREFIX_RE.search(line)
        if not number:
            continue
        case_number = normalize_space(number.group(0))
        suffix = cleanup_case_type(line[number.end() :])
        if suffix:
            return case_number, suffix

        prefix = cleanup_case_type(line[: number.start()])
        if prefix and not DATE_RE.search(prefix):
            return case_number, prefix

        idx = lines.index(line)
        if idx + 1 < len(lines):
            nxt = cleanup_case_type(lines[idx + 1])
            if nxt and not CASE_NUMBER_RE.search(nxt) and not DATE_RE.search(nxt):
                return case_number, nxt
        return case_number, None

    fallback = CASE_NUMBER_RE.search(full_text) or CASE_WITH_PREFIX_RE.search(full_text)
    return (normalize_space(fallback.group(0)), None) if fallback else (None, None)


def set_page_param_from_result_url(result_url: str, page_number: int) -> str:
    parsed = urlparse(result_url)
    query_pairs = parse_qsl(parsed.query, keep_blank_values=True)

    out_pairs: list[tuple[str, str]] = []
    seen_page = False
    seen_court = False
    for k, v in query_pairs:
        if k == "page":
            if not seen_page:
                seen_page = True
                if page_number > 1:
                    out_pairs.append((k, str(page_number)))
            continue
        out_pairs.append((k, v))
        if k == "court":
            seen_court = True

    if not seen_court:
        out_pairs.append(("court", "tsi"))
    if page_number > 1 and not seen_page:
        out_pairs.append(("page", str(page_number)))

    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(out_pairs), parsed.fragment))


def wait_for_results_stable(page: "Page") -> None:
    script = r"""
    () => {
      const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
      const caseRe = /(?:\b\d{1,6}\/\d{4}\b|\b[A-Z]{1,8}-?\d{1,6}\/\d{2,4}\b)/i;
      const dateRe = /(?:\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]\d{4}|\d{4}年\d{1,2}月\d{1,2}日)/;
      const nodes = Array.from(document.querySelectorAll('div,li,article,section,tr'));
      let count = 0;
      for (const el of nodes) {
        const t = norm(el.innerText || '');
        if (!t || t.length < 30) continue;
        let score = 0;
        if (caseRe.test(t)) score += 1;
        if (dateRe.test(t)) score += 1;
        if (t.includes('主題') || t.toLowerCase().includes('subject')) score += 1;
        if (t.includes('摘要') || t.toLowerCase().includes('summary')) score += 1;
        if (score >= 2) count += 1;
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
      const caseRe = /(?:\b\d{1,6}\/\d{4}\b|\b[A-Z]{1,8}-?\d{1,6}\/\d{2,4}\b)/i;
      const dateRe = /(?:\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]\d{4}|\d{4}年\d{1,2}月\d{1,2}日)/;

      const nodes = Array.from(document.querySelectorAll('div,li,article,section,tr'));
      const sigCount = new Map();
      for (const el of nodes) {
        const cls = norm(el.className || '').replace(/\s+/g, '.');
        const sig = `${el.tagName}|${cls}`;
        sigCount.set(sig, (sigCount.get(sig) || 0) + 1);
      }

      const candidates = [];
      nodes.forEach((el, idx) => {
        const txt = norm(el.innerText || '');
        if (!txt || txt.length < 30 || txt.length > 3500) return;
        const cls = norm(el.className || '').replace(/\s+/g, '.');
        const sig = `${el.tagName}|${cls}`;
        const repeated = sigCount.get(sig) || 0;
        if (repeated < 3) return;

        let score = 0;
        if (caseRe.test(txt)) score += 2;
        if (dateRe.test(txt)) score += 1;
        if (txt.includes('主題') || txt.toLowerCase().includes('subject')) score += 1;
        if (txt.includes('摘要') || txt.toLowerCase().includes('summary')) score += 1;
        if (txt.includes('裁判結果') || txt.toLowerCase().includes('resultado')) score += 1;

        const docNodes = Array.from(el.querySelectorAll('a,button,[role="button"],span,i')).map((n) => ({
          tag: (n.tagName || '').toLowerCase(),
          href: n.getAttribute('href') || '',
          onclick: n.getAttribute('onclick') || '',
          data_href: n.getAttribute('data-href') || '',
          data_url: n.getAttribute('data-url') || '',
          data_target: n.getAttribute('data-target') || '',
          title: n.getAttribute('title') || '',
          aria_label: n.getAttribute('aria-label') || '',
          class_name: n.getAttribute('class') || '',
          text: norm(n.innerText || ''),
        }));

        if (score < 3) return;

        const lines = (el.innerText || '')
          .split(/\n+/)
          .map((x) => norm(x))
          .filter(Boolean)
          .slice(0, 80);

        candidates.push({
          idx,
          signature: sig,
          repeated_count: repeated,
          score,
          raw_card_text: txt,
          lines,
          doc_nodes: docNodes,
          element: el,
        });
      });

      // Avoid merged records: keep most atomic candidates.
      const candidateSet = new Set(candidates.map((c) => c.idx));
      const hasCandidateDescendant = (candidate) => {
        for (const other of candidates) {
          if (other.idx === candidate.idx) continue;
          if (candidate.element.contains(other.element)) return true;
        }
        return false;
      };

      const atomic = candidates.filter((c) => !hasCandidateDescendant(c));
      const selected = atomic.length >= 3 ? atomic : candidates;

      // strip element references before return
      return selected.map((c) => ({
        idx: c.idx,
        signature: c.signature,
        repeated_count: c.repeated_count,
        score: c.score,
        raw_card_text: c.raw_card_text,
        lines: c.lines,
        doc_nodes: c.doc_nodes,
      }));
    }
    """
    return page.evaluate(script)


def detect_doc_candidate(node: dict[str, Any]) -> dict[str, Any] | None:
    attrs = {
        "href": normalize_space(node.get("href")),
        "onclick": normalize_space(node.get("onclick")),
        "data_href": normalize_space(node.get("data_href")),
        "data_url": normalize_space(node.get("data_url")),
        "data_target": normalize_space(node.get("data_target")),
        "title": normalize_space(node.get("title")),
        "aria_label": normalize_space(node.get("aria_label")),
        "class_name": normalize_space(node.get("class_name")),
    }
    text = normalize_space(node.get("text"))
    joined = " ".join([text, *attrs.values()]).lower()
    if not joined:
        return None

    has_doc_hint = any(k in joined for k in PDF_HINTS + TEXT_HINTS) or "/sentence/" in joined
    has_action = bool(attrs["onclick"] or attrs["data_target"])
    has_target = bool(attrs["href"] or attrs["data_href"] or attrs["data_url"])
    if not (has_doc_hint or has_action or has_target):
        return None

    href_like = attrs["href"] or attrs["data_href"] or attrs["data_url"]
    href = normalize_url_or_action(href_like)

    action = None
    if attrs["onclick"]:
        action = f"action:onclick={attrs['onclick']}"
    elif attrs["data_target"]:
        action = f"action:data-target={attrs['data_target']}"
    elif href_like.lower().startswith("javascript:"):
        action = f"action:{href_like}"

    return {
        "href": href,
        "action": action,
        "is_pdf": any(k in joined for k in PDF_HINTS),
        "is_zh_sentence": bool(ZH_SENTENCE_RE.search(joined)),
        "is_pt_sentence": bool(PT_SENTENCE_RE.search(joined)),
        "is_text": bool(any(k in joined for k in TEXT_HINTS) or ZH_SENTENCE_RE.search(joined) or PT_SENTENCE_RE.search(joined)),
    }


def select_pdf_and_text(candidates: list[dict[str, Any]]) -> tuple[str | None, str | None, str | None]:
    pdf_url = None
    text_target = None
    text_lang = None

    for c in candidates:
        target = c.get("href") or c.get("action")
        if target and c.get("is_zh_sentence"):
            text_target = str(target)
            text_lang = "zh"
            break
    if not text_target:
        for c in candidates:
            target = c.get("href") or c.get("action")
            if target and c.get("is_pt_sentence"):
                text_target = str(target)
                text_lang = "pt"
                break
    if not text_target:
        for c in candidates:
            target = c.get("href") or c.get("action")
            if target and c.get("is_text"):
                text_target = str(target)
                break

    for c in candidates:
        target = c.get("href")
        if target and c.get("is_pdf"):
            pdf_url = str(target)
            break

    return pdf_url, text_target, text_lang


def parse_card(card: dict[str, Any], court_label: str, page_number: int) -> dict[str, Any]:
    raw_text = normalize_space(card.get("raw_card_text"))
    lines = [normalize_space(x) for x in (card.get("lines") or []) if normalize_space(x)]
    decision_date_match = DATE_RE.search(raw_text)
    case_number, case_type = parse_case_number_and_type(lines, raw_text)

    subject = extract_labeled_field(lines, SUBJECT_KEYS)
    summary = extract_labeled_field(lines, SUMMARY_KEYS)
    decision_result = extract_labeled_field(lines, DECISION_RESULT_KEYS)
    reporting_judge = extract_labeled_field(lines, REPORTING_JUDGE_KEYS)
    assistant_judges = extract_labeled_field(lines, ASSISTANT_JUDGE_KEYS)

    nodes = card.get("doc_nodes") or []
    candidates = [c for n in nodes if (c := detect_doc_candidate(n))]
    pdf_url, text_url_or_action, text_link_language = select_pdf_and_text(candidates)

    return {
        "court": court_label,
        "decision_date": decision_date_match.group(0) if decision_date_match else None,
        "case_number": case_number,
        "case_type": cleanup_case_type(case_type),
        "pdf_url": pdf_url,
        "text_url_or_action": text_url_or_action,
        "subject": subject,
        "summary": summary,
        "decision_result": decision_result,
        "reporting_judge": reporting_judge,
        "assistant_judges": assistant_judges,
        "raw_card_text": raw_text or None,
        "page_number": page_number,
        "text_link_language": text_link_language,
    }


def evaluate_page_validity(cards: list[dict[str, Any]]) -> tuple[bool, str | None, int, int]:
    parsed_count = len(cards)
    case_count = sum(1 for c in cards if CASE_NUMBER_RE.fullmatch(normalize_space(c.get("case_number"))))
    doc_count = sum(1 for c in cards if normalize_space(c.get("pdf_url")) or normalize_space(c.get("text_url_or_action")))
    if parsed_count < 5:
        return False, "parsed_cards_below_5", case_count, doc_count
    if case_count < 3:
        return False, "cards_with_valid_case_number_below_3", case_count, doc_count
    if doc_count < 3:
        return False, "cards_with_doc_links_below_3", case_count, doc_count
    return True, None, case_count, doc_count


def page_looks_like_search_form(page: "Page") -> bool:
    script = r"""
    () => {
      const norm = (s) => (s || '').replace(/\s+/g, ' ').trim().toLowerCase();
      const pageText = norm(document.body?.innerText || '');
      const controls = document.querySelectorAll('form input, form select, form button, form textarea').length;
      const forms = document.querySelectorAll('form').length;
      const hasSearchWords = ['搜索', '查詢', 'search', 'pesquisa', '法院', 'court'].filter((k) => pageText.includes(k)).length >= 3;
      return forms > 0 && controls >= 6 && hasSearchWords;
    }
    """
    return bool(page.evaluate(script))


def dedupe_cards(cards: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[Any, ...]] = set()
    out: list[dict[str, Any]] = []
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
        out.append(card)
    return out


def submit_real_search(page: "Page", court_code: str) -> tuple[bool, str | None]:
    page.goto(f"{BASE_URL}{RESULT_PATH}", wait_until="domcontentloaded", timeout=45_000)
    page.wait_for_timeout(1200)

    selector = page.locator("#wizcasesearch_sentence_filter_type_court")
    target_label = COURT_LABEL_MAP.get(court_code, "")
    try:
        selector.wait_for(timeout=5000)
        selector.select_option(value=court_code)
    except Exception:
        try:
            if target_label:
                selector.select_option(label=target_label)
            else:
                return False, None
        except Exception:
            return False, None

    form = page.locator("form[action*='researchjudgments']").last
    try:
        form.wait_for(timeout=5000)
    except Exception:
        return False, None

    clicked = False
    for sel in ["button[type='submit']", "input[type='submit']", "button:has-text('搜尋')", "button", "input[type='button']"]:
        btns = form.locator(sel)
        if btns.count() == 0:
            continue
        for i in range(btns.count()):
            try:
                target = btns.nth(i)
                if target.is_visible():
                    target.scroll_into_view_if_needed()
                    target.click(timeout=5000, force=True)
                    clicked = True
                    break
            except Exception:
                continue
        if clicked:
            break

    if not clicked:
        try:
            form.evaluate("(f) => f.submit()")
            clicked = True
        except Exception:
            clicked = False

    if not clicked:
        return False, None

    page.wait_for_timeout(1000)
    page.wait_for_load_state("domcontentloaded", timeout=45_000)
    wait_for_results_stable(page)
    return True, page.url


def parse_page_at_url(page: "Page", url: str, court_label: str, page_number: int) -> tuple[PageAttempt, list[dict[str, Any]]]:
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=45_000)
        page.wait_for_timeout(1200)
        wait_for_results_stable(page)

        blocks = extract_card_blocks_from_dom(page)
        cards = [parse_card(b, court_label, page_number) for b in blocks]
        valid, reason, case_count, doc_count = evaluate_page_validity(cards)
        if not valid and page_looks_like_search_form(page):
            reason = "search_form_like_page_detected"

        if not valid:
            return (
                PageAttempt(page_number, url, False, len(blocks), len(cards), case_count, doc_count, False, invalid_reason=reason),
                [],
            )

        return (
            PageAttempt(page_number, url, True, len(blocks), len(cards), case_count, doc_count, True),
            cards,
        )
    except Exception as exc:
        return (
            PageAttempt(page_number, url, False, 0, 0, 0, 0, False, error=str(exc)),
            [],
        )


def is_valid_case_type(case_type: str | None) -> bool:
    value = normalize_space(case_type)
    if not value:
        return False
    if re.fullmatch(r"/\d{2,4}", value):
        return False
    return True


def is_contaminated(card: dict[str, Any]) -> bool:
    raw = normalize_space(card.get("raw_card_text"))
    if not raw:
        return True
    case_hits = len(CASE_NUMBER_RE.findall(raw)) + len(CASE_WITH_PREFIX_RE.findall(raw))
    date_hits = len(DATE_RE.findall(raw))
    label_hits = sum(raw.count(k) for k in ("主題", "摘要", "裁判結果"))
    return case_hits > 1 or date_hits > 1 or label_hits > 6


def compute_metrics(cards: list[dict[str, Any]]) -> dict[str, int | bool]:
    valid_case_number = sum(1 for c in cards if CASE_NUMBER_RE.fullmatch(normalize_space(c.get("case_number"))))
    valid_case_type = sum(1 for c in cards if is_valid_case_type(c.get("case_type")))
    contaminated = sum(1 for c in cards if is_contaminated(c))
    cards_with_text = sum(1 for c in cards if normalize_space(c.get("text_url_or_action")))
    cards_with_pdf = sum(1 for c in cards if normalize_space(c.get("pdf_url")))
    success = bool(cards) and contaminated == 0 and valid_case_number >= max(1, int(len(cards) * 0.6)) and valid_case_type >= max(1, int(len(cards) * 0.6))
    return {
        "valid_case_number_count": valid_case_number,
        "valid_case_type_count": valid_case_type,
        "records_suspected_of_multi_card_contamination": contaminated,
        "cards_with_text": cards_with_text,
        "cards_with_pdf": cards_with_pdf,
        "card_boundary_fix_success": success,
    }


def build_report(
    court_code: str,
    start_state_url: str | None,
    page1_real_result_reached: bool,
    attempts: list[PageAttempt],
    total_before: int,
    total_after: int,
    cards: list[dict[str, Any]],
) -> str:
    pages_attempted = [a.page_number for a in attempts]
    valid_pages = [a.page_number for a in attempts if a.valid_result_page]
    metric = compute_metrics(cards)

    lines = [
        "# Day 16A result-card boundary fix report",
        f"court code used: {court_code}",
        f"court label: {COURT_LABEL_MAP.get(court_code, 'unknown')}",
        f"submitted result-state url: {start_state_url}",
        f"page 1 real result page reached: {'yes' if page1_real_result_reached else 'no'}",
        f"pages parsed: {valid_pages}",
        f"pages attempted: {pages_attempted}",
        f"total cards before dedupe: {total_before}",
        f"total cards after dedupe: {total_after}",
        f"valid case_number count: {metric['valid_case_number_count']}",
        f"valid case_type count: {metric['valid_case_type_count']}",
        f"records suspected of multi-card contamination: {metric['records_suspected_of_multi_card_contamination']}",
        f"cards with pdf_url: {metric['cards_with_pdf']}",
        f"cards with text_url_or_action: {metric['cards_with_text']}",
        f"whether card-boundary fix appears successful: {metric['card_boundary_fix_success']}",
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
                    "valid_result_page": a.valid_result_page,
                    "invalid_reason": a.invalid_reason,
                    "card_blocks": a.card_blocks,
                    "parsed_cards": a.parsed_cards,
                    "cards_with_case_number": a.cards_with_case_number,
                    "cards_with_doc_links": a.cards_with_doc_links,
                    "error": a.error,
                },
                ensure_ascii=False,
            )
        )

    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Day 16A card-boundary fix extractor for paginated court result cards.")
    parser.add_argument("--court", default="tsi", choices=sorted(COURT_LABEL_MAP.keys()))
    parser.add_argument("--pages", type=int, default=3)
    args = parser.parse_args()

    PARSED_DIR.mkdir(parents=True, exist_ok=True)

    attempts: list[PageAttempt] = []
    all_cards: list[dict[str, Any]] = []
    court_label = COURT_LABEL_MAP.get(args.court, "unknown")
    page1_real_result_reached = False
    start_state_url: str | None = None

    sync_playwright = load_playwright()
    if not sync_playwright:
        deduped_cards: list[dict[str, Any]] = []
        for n in range(1, max(1, args.pages) + 1):
            attempts.append(
                PageAttempt(
                    page_number=n,
                    url=f"{BASE_URL}{RESULT_PATH}",
                    success=False,
                    card_blocks=0,
                    parsed_cards=0,
                    cards_with_case_number=0,
                    cards_with_doc_links=0,
                    valid_result_page=False,
                    error="playwright_not_installed",
                )
            )
    else:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(locale="zh-HK")
            page = context.new_page()

            submitted, result_state_url = submit_real_search(page, args.court)
            if submitted and result_state_url:
                start_state_url = result_state_url
                page1_url = set_page_param_from_result_url(result_state_url, 1)
                attempt1, cards1 = parse_page_at_url(page, page1_url, court_label, 1)
                attempts.append(attempt1)
                all_cards.extend(cards1)
                page1_real_result_reached = attempt1.valid_result_page

                if page1_real_result_reached:
                    real_result_state_url = page.url
                    for n in range(2, max(1, args.pages) + 1):
                        next_url = set_page_param_from_result_url(real_result_state_url, n)
                        attempt, cards = parse_page_at_url(page, next_url, court_label, n)
                        attempts.append(attempt)
                        all_cards.extend(cards)
            else:
                for n in range(1, max(1, args.pages) + 1):
                    attempts.append(
                        PageAttempt(
                            page_number=n,
                            url=f"{BASE_URL}{RESULT_PATH}",
                            success=False,
                            card_blocks=0,
                            parsed_cards=0,
                            cards_with_case_number=0,
                            cards_with_doc_links=0,
                            valid_result_page=False,
                            invalid_reason="failed_to_submit_real_search",
                        )
                    )

            browser.close()

        deduped_cards = dedupe_cards(all_cards)

    OUTPUT_JSON_PATH.write_text(json.dumps(deduped_cards, ensure_ascii=False, indent=2), encoding="utf-8")
    metric = compute_metrics(deduped_cards)
    OUTPUT_REPORT_PATH.write_text(
        build_report(args.court, start_state_url, page1_real_result_reached, attempts, len(all_cards), len(deduped_cards), deduped_cards),
        encoding="utf-8",
    )

    valid_pages = [a.page_number for a in attempts if a.valid_result_page]
    print(f"pages parsed: {valid_pages}")
    print(f"total cards before dedupe: {len(all_cards)}")
    print(f"total cards after dedupe: {len(deduped_cards)}")
    print(f"valid case_number count: {metric['valid_case_number_count']}")
    print(f"valid case_type count: {metric['valid_case_type_count']}")
    print(f"records suspected of multi-card contamination: {metric['records_suspected_of_multi_card_contamination']}")
    print(f"whether card-boundary fix appears successful: {metric['card_boundary_fix_success']}")
    print(f"output json: {OUTPUT_JSON_PATH}")
    print(f"report path: {OUTPUT_REPORT_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
