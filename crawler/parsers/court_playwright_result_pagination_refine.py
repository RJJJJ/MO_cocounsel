"""Day 15: refine paginated result-card extraction to preserve text/fulltext links.

Scope:
- reuse Day 14 stateful pagination flow (real submitted search-result state)
- parse pages 1..N (default 3)
- strengthen in-card document link/action extraction for PDF + text/fulltext
- preserve sentence links (zh/pt) and action descriptors when href is absent

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
OUTPUT_JSON_PATH = PARSED_DIR / "playwright_result_cards_paginated_refined.json"
OUTPUT_REPORT_PATH = PARSED_DIR / "playwright_pagination_refined_report.txt"

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

PDF_HINTS = ("pdf", ".pdf", "判決書")
TEXT_HINTS = (
    "全文",
    "text",
    "fulltext",
    "full text",
    "teor",
    "conteúdo",
    "conteudo",
    "sentença",
    "sentenca",
    "sentence",
    "裁判書",
)
ZH_SENTENCE_RE = re.compile(r"/sentence/zh/\d+/?", re.IGNORECASE)
PT_SENTENCE_RE = re.compile(r"/sentence/pt/\d+/?", re.IGNORECASE)


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
    cards_with_case_number: int
    cards_with_doc_links: int
    valid_result_page: bool
    invalid_reason: str | None = None
    error: str | None = None


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


def extract_field_by_label(text: str, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        m = re.search(rf"{re.escape(key)}\s*[:：]?\s*([^\n\r]+)", text, flags=re.IGNORECASE)
        if m:
            v = normalize_space(m.group(1))
            if v:
                return v
    return None


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

        const docNodes = Array.from(el.querySelectorAll('a,button,[role="button"],span,i')).map((n) => {
          const attrs = [
            n.getAttribute('href') || '',
            n.getAttribute('onclick') || '',
            n.getAttribute('data-href') || '',
            n.getAttribute('data-url') || '',
            n.getAttribute('title') || '',
            n.getAttribute('aria-label') || '',
            n.getAttribute('class') || '',
            norm(n.innerText || ''),
          ].join(' ').toLowerCase();
          return attrs;
        });

        if (docNodes.some((x) => x.includes('pdf'))) score += 1;
        if (docNodes.some((x) => x.includes('/sentence/') || x.includes('全文') || x.includes('text') || x.includes('teor'))) score += 1;

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
        if (!rawText || rawText.length < 40 || rawText.length > 4500) continue;

        const cls = norm(el.className || '').replace(/\s+/g, '.');
        const signature = `${el.tagName}|${cls}`;
        const repeatedCount = sigMap.get(signature) || 0;
        if (repeatedCount < 3) continue;

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

        let score = 0;
        if (dateRe.test(rawText)) score += 1;
        if (caseRe.test(rawText)) score += 1;
        if (rawText.includes('主題') || rawText.toLowerCase().includes('subject')) score += 1;
        if (rawText.includes('摘要') || rawText.toLowerCase().includes('summary')) score += 1;
        if (rawText.includes('裁判結果') || rawText.toLowerCase().includes('resultado')) score += 1;

        const flatNodes = docNodes.map((n) => `${n.href} ${n.onclick} ${n.data_href} ${n.data_url} ${n.title} ${n.aria_label} ${n.class_name} ${n.text}`.toLowerCase());
        if (flatNodes.some((v) => v.includes('pdf'))) score += 1;
        if (flatNodes.some((v) => v.includes('/sentence/') || v.includes('全文') || v.includes('text') || v.includes('teor'))) score += 1;

        if (score < 3) continue;

        out.push({ raw_card_text: rawText, signature, repeated_count: repeatedCount, score, doc_nodes: docNodes });
      }
      return out;
    }
    """
    return page.evaluate(script)


def detect_doc_candidate(node: dict[str, Any]) -> dict[str, Any] | None:
    tag = normalize_space(node.get("tag")).lower()
    text = normalize_space(node.get("text"))
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

    candidate_raw = " ".join([text, *attrs.values()]).lower()
    if not candidate_raw:
        return None

    has_doc_hint = any(k in candidate_raw for k in PDF_HINTS + TEXT_HINTS) or "/sentence/" in candidate_raw
    has_action = any(attrs[k] for k in ("onclick", "data_target"))
    has_target = any(attrs[k] for k in ("href", "data_href", "data_url"))

    if not (has_doc_hint or has_action or has_target):
        return None

    href_like = attrs["href"] or attrs["data_href"] or attrs["data_url"]
    href_value = normalize_url_or_action(href_like)

    action_descriptor = None
    if attrs["onclick"]:
        action_descriptor = f"action:onclick={attrs['onclick']}"
    elif attrs["data_target"]:
        action_descriptor = f"action:data-target={attrs['data_target']}"
    elif href_like.lower().startswith("javascript:"):
        action_descriptor = f"action:{href_like}"

    combined_for_type = " ".join([candidate_raw, href_like.lower()])
    is_pdf = any(k in combined_for_type for k in PDF_HINTS)
    is_zh_sentence = bool(ZH_SENTENCE_RE.search(combined_for_type))
    is_pt_sentence = bool(PT_SENTENCE_RE.search(combined_for_type))
    is_text = is_zh_sentence or is_pt_sentence or any(k in combined_for_type for k in TEXT_HINTS)

    return {
        "tag": tag,
        "text": text,
        "href": href_value,
        "action": action_descriptor,
        "candidate_raw": candidate_raw,
        "is_pdf": is_pdf,
        "is_text": is_text,
        "is_zh_sentence": is_zh_sentence,
        "is_pt_sentence": is_pt_sentence,
    }


def select_pdf_and_text(candidates: list[dict[str, Any]]) -> tuple[str | None, str | None, str | None]:
    pdf_url = None
    text_url_or_action = None
    text_lang = None

    # 1) Prefer explicit sentence links by lang
    for c in candidates:
        target = c.get("href") or c.get("action")
        if not target:
            continue
        if c.get("is_zh_sentence"):
            text_url_or_action = str(target)
            text_lang = "zh"
            break
    if not text_url_or_action:
        for c in candidates:
            target = c.get("href") or c.get("action")
            if not target:
                continue
            if c.get("is_pt_sentence"):
                text_url_or_action = str(target)
                text_lang = "pt"
                break

    # 2) Then generic text/fulltext candidate
    if not text_url_or_action:
        for c in candidates:
            target = c.get("href") or c.get("action")
            if target and c.get("is_text"):
                text_url_or_action = str(target)
                if c.get("is_zh_sentence"):
                    text_lang = "zh"
                elif c.get("is_pt_sentence"):
                    text_lang = "pt"
                break

    # 3) PDF candidate
    for c in candidates:
        target = c.get("href")
        if target and c.get("is_pdf"):
            pdf_url = str(target)
            break

    # 4) fallback: if pdf not found, take href ending .pdf
    if not pdf_url:
        for c in candidates:
            target = str(c.get("href") or "")
            if ".pdf" in target.lower():
                pdf_url = target
                break

    return pdf_url, text_url_or_action, text_lang


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

    nodes = card.get("doc_nodes", [])
    candidates = [c for node in nodes if (c := detect_doc_candidate(node))]
    pdf_url, text_url_or_action, text_link_language = select_pdf_and_text(candidates)

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
        "text_link_language": text_link_language,
    }


def evaluate_page_validity(parsed_cards: list[dict[str, Any]]) -> tuple[bool, str | None, int, int]:
    parsed_count = len(parsed_cards)
    cards_with_case_number = sum(1 for c in parsed_cards if normalize_space(c.get("case_number")))
    cards_with_doc_links = sum(
        1 for c in parsed_cards if normalize_space(c.get("pdf_url")) or normalize_space(c.get("text_url_or_action"))
    )

    if parsed_count < 5:
        return False, "parsed_cards_below_5", cards_with_case_number, cards_with_doc_links
    if cards_with_case_number < 3:
        return False, "cards_with_case_number_below_3", cards_with_case_number, cards_with_doc_links
    if cards_with_doc_links < 3:
        return False, "cards_with_doc_links_below_3", cards_with_case_number, cards_with_doc_links

    return True, None, cards_with_case_number, cards_with_doc_links


def page_looks_like_search_form(page: "Page") -> bool:
    script = r"""
    () => {
      const norm = (s) => (s || '').replace(/\s+/g, ' ').trim().toLowerCase();
      const pageText = norm(document.body?.innerText || '');
      const hasSearchWords = ['搜索', '查詢', '查找', 'search', 'pesquisa', '法院', 'court'].filter((k) => pageText.includes(k)).length >= 3;
      const controls = document.querySelectorAll('form input, form select, form button, form textarea').length;
      const formCount = document.querySelectorAll('form').length;
      const candidateCards = Array.from(document.querySelectorAll('div,li,article,section,tr')).filter((el) => {
        const t = norm(el.innerText || '');
        if (t.length < 40) return false;
        const isCase = /(?:\b[A-Z]{1,6}-?\d{1,6}\/\d{2,4}\b|\b\d{1,6}\/\d{2,4}\b|案(?:件)?(?:編號|號)?[:：\s]*[A-Za-z0-9\-/.]+)/i.test(t);
        const hasDate = /(?:\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]\d{4}|\d{4}年\d{1,2}月\d{1,2}日)/.test(t);
        return isCase && hasDate;
      }).length;
      return formCount > 0 && controls >= 6 && candidateCards < 2 && hasSearchWords;
    }
    """
    return bool(page.evaluate(script))


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


def submit_real_search(page: "Page", court_code: str) -> tuple[bool, str | None]:
    target_url = f"{BASE_URL}{RESULT_PATH}"
    page.goto(target_url, wait_until="domcontentloaded", timeout=45_000)
    page.wait_for_timeout(1200)

    sel = page.locator("#wizcasesearch_sentence_filter_type_court")
    target_label = COURT_LABEL_MAP.get(court_code, "")
    try:
        sel.wait_for(timeout=5000)
        sel.select_option(value=court_code)
    except Exception:
        try:
            if target_label:
                sel.select_option(label=target_label)
            else:
                return False, None
        except Exception:
            return False, None

    form = page.locator("form[action*='researchjudgments']").last
    try:
        form.wait_for(timeout=5000)
    except Exception:
        return False, None

    submit_ok = False
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
                    submit_ok = True
                    break
            except Exception:
                continue
        if submit_ok:
            break

    if not submit_ok:
        try:
            form.evaluate("(f) => f.submit()")
            submit_ok = True
        except Exception:
            submit_ok = False

    if not submit_ok:
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
        cards = [parse_card(block, court_label=court_label, page_number=page_number) for block in blocks]
        valid, invalid_reason, cards_with_case_number, cards_with_doc_links = evaluate_page_validity(cards)
        if not valid and page_looks_like_search_form(page):
            invalid_reason = "search_form_like_page_detected"

        if not valid:
            return (
                PageAttempt(
                    page_number=page_number,
                    url=url,
                    success=False,
                    card_blocks=len(blocks),
                    parsed_cards=len(cards),
                    cards_with_case_number=cards_with_case_number,
                    cards_with_doc_links=cards_with_doc_links,
                    valid_result_page=False,
                    invalid_reason=invalid_reason,
                ),
                [],
            )

        return (
            PageAttempt(
                page_number=page_number,
                url=url,
                success=True,
                card_blocks=len(blocks),
                parsed_cards=len(cards),
                cards_with_case_number=cards_with_case_number,
                cards_with_doc_links=cards_with_doc_links,
                valid_result_page=True,
            ),
            cards,
        )
    except Exception as exc:
        return (
            PageAttempt(
                page_number=page_number,
                url=url,
                success=False,
                card_blocks=0,
                parsed_cards=0,
                cards_with_case_number=0,
                cards_with_doc_links=0,
                valid_result_page=False,
                error=str(exc),
            ),
            [],
        )


def compute_metrics(cards: list[dict[str, Any]]) -> dict[str, int]:
    cards_with_pdf = sum(1 for c in cards if normalize_space(c.get("pdf_url")))
    cards_with_text = sum(1 for c in cards if normalize_space(c.get("text_url_or_action")))
    cards_with_both = sum(
        1 for c in cards if normalize_space(c.get("pdf_url")) and normalize_space(c.get("text_url_or_action"))
    )
    zh_text_links = sum(1 for c in cards if (c.get("text_link_language") == "zh") or ZH_SENTENCE_RE.search(str(c.get("text_url_or_action") or "")))
    pt_text_links = sum(1 for c in cards if (c.get("text_link_language") == "pt") or PT_SENTENCE_RE.search(str(c.get("text_url_or_action") or "")))
    return {
        "cards_with_pdf": cards_with_pdf,
        "cards_with_text": cards_with_text,
        "cards_with_both": cards_with_both,
        "zh_text_links": zh_text_links,
        "pt_text_links": pt_text_links,
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
    text_link_success = metric["cards_with_text"] > 0 and (metric["zh_text_links"] + metric["pt_text_links"] > 0 or metric["cards_with_both"] > 0)

    lines = [
        "# Day 15 paginated result-card refinement report",
        f"court code used: {court_code}",
        f"court label: {COURT_LABEL_MAP.get(court_code, 'unknown')}",
        f"submitted result-state url: {start_state_url}",
        f"page 1 real result page reached: {'yes' if page1_real_result_reached else 'no'}",
        f"pages parsed: {valid_pages}",
        f"pages attempted: {pages_attempted}",
        f"total cards before dedupe: {total_before}",
        f"total cards after dedupe: {total_after}",
        f"cards with pdf_url: {metric['cards_with_pdf']}",
        f"cards with text_url_or_action: {metric['cards_with_text']}",
        f"cards with both: {metric['cards_with_both']}",
        f"zh text links count: {metric['zh_text_links']}",
        f"pt text links count: {metric['pt_text_links']}",
        f"paginated text-link resolution appears successful: {text_link_success}",
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
    parser = argparse.ArgumentParser(description="Day 15 refined stateful pagination extractor for court result cards.")
    parser.add_argument("--court", default="tsi", choices=sorted(COURT_LABEL_MAP.keys()), help="Court code, default tsi")
    parser.add_argument("--pages", type=int, default=3, help="Number of pages to attempt, default 3")
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

            submitted, result_state_url = submit_real_search(page=page, court_code=args.court)
            if submitted and result_state_url:
                start_state_url = result_state_url
                page1_url = set_page_param_from_result_url(result_state_url, 1)
                attempt1, cards1 = parse_page_at_url(page=page, url=page1_url, court_label=court_label, page_number=1)
                attempts.append(attempt1)
                all_cards.extend(cards1)
                page1_real_result_reached = attempt1.valid_result_page

                if page1_real_result_reached:
                    real_result_state_url = page.url
                    for n in range(2, max(1, args.pages) + 1):
                        next_url = set_page_param_from_result_url(real_result_state_url, n)
                        attempt, cards = parse_page_at_url(page=page, url=next_url, court_label=court_label, page_number=n)
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
    OUTPUT_REPORT_PATH.write_text(
        build_report(
            court_code=args.court,
            start_state_url=start_state_url,
            page1_real_result_reached=page1_real_result_reached,
            attempts=attempts,
            total_before=len(all_cards),
            total_after=len(deduped_cards),
            cards=deduped_cards,
        ),
        encoding="utf-8",
    )

    valid_pages = [a.page_number for a in attempts if a.valid_result_page]
    metric = compute_metrics(deduped_cards)
    text_link_success = metric["cards_with_text"] > 0 and (metric["zh_text_links"] + metric["pt_text_links"] > 0 or metric["cards_with_both"] > 0)

    print(f"pages parsed: {valid_pages}")
    print(f"total cards before dedupe: {len(all_cards)}")
    print(f"total cards after dedupe: {len(deduped_cards)}")
    print(f"cards with pdf_url: {metric['cards_with_pdf']}")
    print(f"cards with text_url_or_action: {metric['cards_with_text']}")
    print(f"cards with both: {metric['cards_with_both']}")
    print(f"zh text links count: {metric['zh_text_links']}")
    print(f"pt text links count: {metric['pt_text_links']}")
    print(f"paginated text-link resolution appears successful: {text_link_success}")
    print(f"output json: {OUTPUT_JSON_PATH}")
    print(f"report path: {OUTPUT_REPORT_PATH}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
