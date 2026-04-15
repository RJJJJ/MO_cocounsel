"""Day 16C: DOM reconnaissance probe for Macau Courts result and sentence pages.

Scope:
- Open official judgment search page in a real browser (Playwright)
- Select 中級法院 and perform a real search submission
- Inspect rendered DOM on result page
- Open 1-2 TXT/fulltext sentence pages and inspect rendered DOM
- Save reconnaissance artifacts for later parser implementation

Non-goals:
- No parser refactor
- No batch extraction
- No database integration
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from playwright.sync_api import Page, TimeoutError, sync_playwright

TARGET_URL = "https://www.court.gov.mo/zh/subpage/researchjudgments"
BASE_URL = "https://www.court.gov.mo"
OUTPUT_DIR = Path("data/raw/court_probe")

RESULT_HTML_PATH = OUTPUT_DIR / "dom_recon_result_page.html"
RESULT_SCREENSHOT_PATH = OUTPUT_DIR / "dom_recon_result_page.png"
RESULT_CANDIDATES_PATH = OUTPUT_DIR / "dom_recon_result_page_candidates.json"

SENTENCE_HTML_PATH_1 = OUTPUT_DIR / "dom_recon_sentence_page_1.html"
SENTENCE_SCREENSHOT_PATH_1 = OUTPUT_DIR / "dom_recon_sentence_page_1.png"
SENTENCE_CANDIDATES_PATH = OUTPUT_DIR / "dom_recon_sentence_candidates.json"


def _safe_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def select_intermediate_court(page: Page) -> bool:
    selector = page.locator("#wizcasesearch_sentence_filter_type_court")
    try:
        selector.wait_for(timeout=10_000)
        selector.select_option(label="中級法院")
        return True
    except Exception:
        return False


def submit_search(page: Page) -> bool:
    form = page.locator("form[action*='researchjudgments']").last
    try:
        form.wait_for(timeout=8_000)
    except Exception:
        return False

    candidate_selectors = [
        "button[type='submit']",
        "input[type='submit']",
        "button:has-text('搜尋')",
        "button:has-text('搜索')",
        "input[value='搜尋']",
        "input[value='搜索']",
    ]

    for css in candidate_selectors:
        nodes = form.locator(css)
        for i in range(nodes.count()):
            target = nodes.nth(i)
            try:
                if target.is_visible():
                    target.scroll_into_view_if_needed()
                    target.click(timeout=5_000, force=True)
                    return True
            except Exception:
                continue

    try:
        form.evaluate("(f) => f.submit()")
        return True
    except Exception:
        return False


def wait_result_dom_stable(page: Page) -> None:
    script = r"""
    () => {
      const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
      const dateRe = /(?:\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]\d{4}|\d{4}年\d{1,2}月\d{1,2}日)/;
      const caseRe = /(?:\b[A-Z]{1,8}-?\d{1,8}\/\d{2,4}\b|\b\d{1,8}\/\d{2,4}\b|案(?:件)?(?:編號|號)?[:：\s]*[A-Za-z0-9\-/.]+)/i;
      const nodes = Array.from(document.querySelectorAll('div,li,article,section,tr'));
      let scoreCount = 0;
      for (const el of nodes) {
        const text = norm(el.innerText || '');
        if (!text || text.length < 40 || text.length > 4000) continue;
        let score = 0;
        if (dateRe.test(text)) score += 1;
        if (caseRe.test(text)) score += 1;
        const links = Array.from(el.querySelectorAll('a[href]')).map((a) => `${a.getAttribute('href') || ''} ${norm(a.innerText || '')}`.toLowerCase());
        if (links.some((v) => v.includes('pdf'))) score += 1;
        if (links.some((v) => v.includes('全文') || v.includes('text') || v.includes('teor') || v.includes('txt'))) score += 1;
        if (score >= 3) scoreCount += 1;
      }
      return scoreCount;
    }
    """

    previous = -1
    stable_rounds = 0
    for _ in range(24):
        current = int(page.evaluate(script))
        if current > 0 and current == previous:
            stable_rounds += 1
            if stable_rounds >= 3:
                return
        else:
            stable_rounds = 0
        previous = current
        page.wait_for_timeout(700)


def analyze_result_page(page: Page) -> dict[str, Any]:
    script = r"""
    () => {
      const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
      const dateRe = /(?:\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]\d{4}|\d{4}年\d{1,2}月\d{1,2}日)/;
      const caseRe = /(?:\b[A-Z]{1,8}-?\d{1,8}\/\d{2,4}\b|\b\d{1,8}\/\d{2,4}\b|案(?:件)?(?:編號|號)?[:：\s]*[A-Za-z0-9\-/.]+)/i;

      const signature = (el) => {
        const id = norm(el.id || '');
        const classes = Array.from(el.classList || []).slice(0, 6).join('.');
        return `${el.tagName.toLowerCase()}#${id}.${classes}`;
      };

      const nodes = Array.from(document.querySelectorAll('div,li,article,section,tr'));
      const grouped = new Map();

      for (const el of nodes) {
        const sig = signature(el);
        if (!grouped.has(sig)) grouped.set(sig, []);
        grouped.get(sig).push(el);
      }

      const candidates = [];
      for (const [sig, elements] of grouped.entries()) {
        if (elements.length < 2) continue;

        const textLens = [];
        let dateHits = 0;
        let caseHits = 0;
        let pdfHits = 0;
        let txtHits = 0;

        for (const el of elements) {
          const text = norm(el.innerText || '');
          if (text.length === 0 || text.length > 5000) continue;
          textLens.push(text.length);
          if (dateRe.test(text)) dateHits += 1;
          if (caseRe.test(text)) caseHits += 1;
          const linkVectors = Array.from(el.querySelectorAll('a[href]')).map((a) => `${a.getAttribute('href') || ''} ${norm(a.innerText || '')}`.toLowerCase());
          if (linkVectors.some((v) => v.includes('pdf'))) pdfHits += 1;
          if (linkVectors.some((v) => v.includes('全文') || v.includes('text') || v.includes('teor') || v.includes('txt'))) txtHits += 1;
        }

        if (!textLens.length) continue;
        const sorted = [...textLens].sort((a,b) => a - b);
        const median = sorted[Math.floor(sorted.length / 2)];
        const min = sorted[0];
        const max = sorted[sorted.length - 1];
        const avg = Math.round(sorted.reduce((a,b) => a + b, 0) / sorted.length);

        const heuristicScore =
          (elements.length >= 3 ? 2 : 0) +
          (dateHits > 0 ? 1 : 0) +
          (caseHits > 0 ? 1 : 0) +
          (pdfHits > 0 ? 1 : 0) +
          (txtHits > 0 ? 1 : 0) +
          (avg >= 100 ? 1 : 0);

        candidates.push({
          signature: sig,
          tag_name: elements[0].tagName.toLowerCase(),
          id: norm(elements[0].id || ''),
          class_name: norm(elements[0].className || ''),
          repetition_count: elements.length,
          text_length_distribution: { min, median, avg, max },
          contains_date_like_text: dateHits > 0,
          contains_case_number_like_text: caseHits > 0,
          contains_pdf_link: pdfHits > 0,
          contains_txt_or_fulltext_link: txtHits > 0,
          support_counts: {
            date_like_hits: dateHits,
            case_like_hits: caseHits,
            pdf_link_hits: pdfHits,
            txt_link_hits: txtHits,
          },
          heuristic_score: heuristicScore,
        });
      }

      candidates.sort((a, b) => b.heuristic_score - a.heuristic_score || b.repetition_count - a.repetition_count);

      const topForSub = candidates.slice(0, 8).map((c) => c.signature);
      const headerCandidates = [];
      const metaCandidates = [];

      for (const sig of topForSub) {
        const first = nodes.find((n) => signature(n) === sig);
        if (!first) continue;

        const headerSelectors = ['h1','h2','h3','header','.title','.case-title','.card-header','.panel-heading'];
        for (const hs of headerSelectors) {
          const found = first.querySelector(hs);
          if (!found) continue;
          headerCandidates.push({
            parent_signature: sig,
            selector: hs,
            tag_name: found.tagName.toLowerCase(),
            class_name: norm(found.className || ''),
            text_preview: norm((found.innerText || '').slice(0, 200)),
          });
        }

        const metaSelectors = ['.meta','.metadata','.small','.text-muted','ul','dl','table','tbody'];
        for (const ms of metaSelectors) {
          const found = first.querySelector(ms);
          if (!found) continue;
          const text = norm(found.innerText || '');
          if (text.length < 12) continue;
          metaCandidates.push({
            parent_signature: sig,
            selector: ms,
            tag_name: found.tagName.toLowerCase(),
            class_name: norm(found.className || ''),
            text_preview: text.slice(0, 220),
          });
        }
      }

      const txtLinks = [];
      for (const a of Array.from(document.querySelectorAll('a[href]'))) {
        const href = a.getAttribute('href') || '';
        const text = norm(a.innerText || '');
        const v = `${href} ${text}`.toLowerCase();
        if (v.includes('全文') || v.includes('fulltext') || v.includes('text') || v.includes('teor') || v.includes('txt')) {
          txtLinks.push({ href, text });
        }
      }

      return {
        url: window.location.href,
        title: document.title,
        repeated_card_candidates: candidates,
        card_header_candidates: headerCandidates.slice(0, 40),
        metadata_block_candidates: metaCandidates.slice(0, 40),
        txt_link_candidates: txtLinks.slice(0, 50),
      };
    }
    """
    return page.evaluate(script)


def analyze_sentence_page(page: Page, url: str, index: int) -> dict[str, Any]:
    page.goto(url, wait_until="domcontentloaded", timeout=45_000)
    try:
        page.wait_for_load_state("networkidle", timeout=18_000)
    except TimeoutError:
        pass
    page.wait_for_timeout(1_500)

    if index == 1:
        SENTENCE_HTML_PATH_1.write_text(page.content(), encoding="utf-8")
        page.screenshot(path=str(SENTENCE_SCREENSHOT_PATH_1), full_page=True)

    script = r"""
    () => {
      const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
      const dateRe = /(?:\d{4}[./-]\d{1,2}[./-]\d{1,2}|\d{1,2}[./-]\d{1,2}[./-]\d{4}|\d{4}年\d{1,2}月\d{1,2}日)/;
      const caseRe = /(?:\b[A-Z]{1,8}-?\d{1,8}\/\d{2,4}\b|\b\d{1,8}\/\d{2,4}\b|案(?:件)?(?:編號|號)?[:：\s]*[A-Za-z0-9\-/.]+)/i;

      const signature = (el) => {
        const id = norm(el.id || '');
        const classes = Array.from(el.classList || []).slice(0, 6).join('.');
        return `${el.tagName.toLowerCase()}#${id}.${classes}`;
      };

      const nodes = Array.from(document.querySelectorAll('main,article,section,div,td,pre,p'));
      const metaCandidates = [];
      const bodyCandidates = [];

      for (const el of nodes) {
        const text = norm(el.innerText || '');
        if (!text || text.length < 20 || text.length > 120000) continue;

        const hasDate = dateRe.test(text);
        const hasCase = caseRe.test(text);
        const hasIssue = /(主題|爭點|摘要|sumário|sumario|subject|issue)/i.test(text);

        if ((hasDate || hasCase || hasIssue) && text.length <= 5000) {
          metaCandidates.push({
            signature: signature(el),
            tag_name: el.tagName.toLowerCase(),
            id: norm(el.id || ''),
            class_name: norm(el.className || ''),
            text_length: text.length,
            has_date: hasDate,
            has_case_number: hasCase,
            has_title_or_issue: hasIssue,
            text_preview: text.slice(0, 240),
          });
        }

        const denseText = text.length >= 800;
        const paragraphCount = el.querySelectorAll('p').length;
        const lineBreakCount = (el.innerText || '').split('\n').filter((x) => norm(x).length > 0).length;
        if (denseText || paragraphCount >= 8 || lineBreakCount >= 25) {
          bodyCandidates.push({
            signature: signature(el),
            tag_name: el.tagName.toLowerCase(),
            id: norm(el.id || ''),
            class_name: norm(el.className || ''),
            text_length: text.length,
            paragraph_count: paragraphCount,
            non_empty_line_count: lineBreakCount,
            body_score: (denseText ? 2 : 0) + (paragraphCount >= 8 ? 1 : 0) + (lineBreakCount >= 25 ? 1 : 0),
            text_preview: text.slice(0, 240),
          });
        }
      }

      metaCandidates.sort((a, b) => b.text_length - a.text_length);
      bodyCandidates.sort((a, b) => b.body_score - a.body_score || b.text_length - a.text_length);

      const pickField = (regexList, source) => {
        for (const regex of regexList) {
          for (const row of source) {
            if (regex.test(row.text_preview)) return row.signature;
          }
        }
        return null;
      };

      const selectorCandidates = {
        case_number: pickField([/案(?:件)?(?:編號|號)?/i, /\b\d{1,8}\/\d{2,4}\b/i], metaCandidates),
        date: pickField([/\d{4}[./-]\d{1,2}[./-]\d{1,2}/, /\d{4}年\d{1,2}月\d{1,2}日/], metaCandidates),
        title_or_issue: pickField([/主題|爭點|摘要|sumário|sumario|subject|issue/i], metaCandidates),
        body: bodyCandidates.length ? bodyCandidates[0].signature : null,
      };

      return {
        url: window.location.href,
        title: document.title,
        metadata_zone_candidates: metaCandidates.slice(0, 40),
        main_body_candidates: bodyCandidates.slice(0, 40),
        field_selector_candidates: selectorCandidates,
      };
    }
    """

    return page.evaluate(script)


def run_dom_recon() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    result_page_reached = False
    sentence_pages_opened = 0
    top_candidates: list[str] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(locale="zh-HK")
            page = context.new_page()

            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=45_000)
            page.wait_for_timeout(1_500)

            court_selected = select_intermediate_court(page)
            submitted = submit_search(page)

            if submitted:
                try:
                    page.wait_for_load_state("networkidle", timeout=20_000)
                except TimeoutError:
                    pass
                wait_result_dom_stable(page)

            result_page_reached = submitted and ("researchjudgments" in page.url)

            RESULT_HTML_PATH.write_text(page.content(), encoding="utf-8")
            page.screenshot(path=str(RESULT_SCREENSHOT_PATH), full_page=True)

            result_analysis = analyze_result_page(page)
            RESULT_CANDIDATES_PATH.write_text(
                json.dumps(
                    {
                        "probe": "day16c_dom_recon_result_page",
                        "target_url": TARGET_URL,
                        "court_selected": court_selected,
                        "search_submitted": submitted,
                        "result_page_reached": result_page_reached,
                        "analysis": result_analysis,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            repeated_candidates = result_analysis.get("repeated_card_candidates", [])
            top_candidates = [
                f"{row.get('signature')} (score={row.get('heuristic_score')}, repeat={row.get('repetition_count')})"
                for row in repeated_candidates[:5]
            ]

            txt_links = result_analysis.get("txt_link_candidates", [])
            absolute_txt_links: list[str] = []
            for item in txt_links:
                href = _safe_text(item.get("href"))
                if not href:
                    continue
                absolute = urljoin(BASE_URL, href)
                if absolute not in absolute_txt_links:
                    absolute_txt_links.append(absolute)
                if len(absolute_txt_links) >= 2:
                    break

            sentence_runs: list[dict[str, Any]] = []
            for idx, link in enumerate(absolute_txt_links, start=1):
                try:
                    detail = analyze_sentence_page(page, link, idx)
                    sentence_runs.append(detail)
                    sentence_pages_opened += 1
                except Exception as exc:
                    sentence_runs.append(
                        {
                            "url": link,
                            "error": f"sentence page open/analyze failed: {exc}",
                        }
                    )

            SENTENCE_CANDIDATES_PATH.write_text(
                json.dumps(
                    {
                        "probe": "day16c_dom_recon_sentence_pages",
                        "source_result_url": result_analysis.get("url"),
                        "txt_links_considered": absolute_txt_links,
                        "sentence_pages_opened": sentence_pages_opened,
                        "pages": sentence_runs,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            browser.close()

            sentence_main_body_count = 0
            if sentence_runs:
                first_ok = next((p for p in sentence_runs if isinstance(p, dict) and p.get("main_body_candidates")), None)
                if first_ok:
                    sentence_main_body_count = len(first_ok.get("main_body_candidates", []))

            success = (
                result_page_reached
                and len(repeated_candidates) > 0
                and sentence_pages_opened > 0
                and sentence_main_body_count > 0
            )

            print(f"result page reached: {'yes' if result_page_reached else 'no'}")
            print(f"repeated card candidate count: {len(repeated_candidates)}")
            print("top card container candidates:")
            if top_candidates:
                for item in top_candidates:
                    print(f"- {item}")
            else:
                print("- (none)")
            print(f"txt links found count: {len(txt_links)}")
            print(f"sentence pages opened count: {sentence_pages_opened}")
            print(f"sentence page main body candidates found count: {sentence_main_body_count}")
            print(f"dom reconnaissance successful: {'yes' if success else 'no'}")

            return 0 if success else 2

    except Exception as exc:
        print(f"dom reconnaissance failed with exception: {exc}")
        print("result page reached: no")
        print("repeated card candidate count: 0")
        print("top card container candidates:")
        print("- (none)")
        print("txt links found count: 0")
        print("sentence pages opened count: 0")
        print("sentence page main body candidates found count: 0")
        print("dom reconnaissance successful: no")
        return 1


def main() -> int:
    return run_dom_recon()


if __name__ == "__main__":
    raise SystemExit(main())
