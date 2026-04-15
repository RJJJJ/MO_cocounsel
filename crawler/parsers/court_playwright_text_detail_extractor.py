"""Day 11: Refined Playwright extractor for Macau Courts result cards + TXT/fulltext detail samples.

Scope:
- reuse Day 10 search flow (single query, no pagination)
- refine result-card field extraction
- resolve TXT/fulltext entry beyond plain href assumptions
- click 1~3 real TXT/fulltext entries and extract text-detail content
- persist refined cards, text-detail samples, and a report
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

from playwright.sync_api import BrowserContext, Page, TimeoutError, sync_playwright

TARGET_URL = "https://www.court.gov.mo/zh/subpage/researchjudgments"
BASE_URL = "https://www.court.gov.mo"

PARSED_DIR = Path("data/parsed/court_probe")
RAW_DIR = Path("data/raw/court_probe")

REFINED_CARDS_PATH = PARSED_DIR / "playwright_result_cards_refined.json"
TEXT_SAMPLES_PATH = PARSED_DIR / "playwright_text_details_sample.json"
REPORT_PATH = PARSED_DIR / "playwright_text_details_report.txt"
RAW_RESULT_HTML_PATH = RAW_DIR / "playwright_result_page_day11.html"

DATE_RE = re.compile(r"\b\d{1,2}/\d{1,2}/\d{4}\b|\b\d{4}[./-]\d{1,2}[./-]\d{1,2}\b")
CASE_NUMBER_RE = re.compile(r"\b\d{1,6}/\d{4}\b")

SUBJECT_KEYS = ("主題", "subject")
SUMMARY_KEYS = ("摘要", "sumário", "sumario", "summary")
RESULT_KEYS = ("表決", "裁判結果", "resultado", "decision")
REPORTING_KEYS = ("裁判書製作人", "裁判書製作法官", "報告法官", "juiz relator")
ASSISTANT_KEYS = ("助審法官", "adjuntos", "assistant")
TEXT_KEYS = ("全文", "txt", "fulltext", "teor", "texto")


@dataclass
class CandidateAction:
    element_selector: str
    href: str | None
    onclick: str | None
    action_type: str
    label: str


def normalize_space(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def fill_recent_30_days(page: Page) -> bool:
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    left = page.locator("#wizcasesearch_sentence_filter_type_decisionDate_left_date")
    right = page.locator("#wizcasesearch_sentence_filter_type_decisionDate_right_date")

    try:
        left.wait_for(timeout=5000)
        right.wait_for(timeout=5000)
        left.fill(start_date.strftime("%d/%m/%Y"))
        right.fill(end_date.strftime("%d/%m/%Y"))
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
        return "unknown"


def click_search(page: Page) -> bool:
    form = page.locator("form[action*='researchjudgments']").last
    try:
        form.wait_for(timeout=5000)
    except Exception:
        return False

    selectors = ["button[type='submit']", "input[type='submit']", "button", "input[type='button']"]
    for selector in selectors:
        btn = form.locator(selector)
        for i in range(btn.count()):
            try:
                b = btn.nth(i)
                if b.is_visible():
                    b.click(timeout=3000, force=True)
                    return True
            except Exception:
                continue

    try:
        form.evaluate("(f) => f.submit()")
        return True
    except Exception:
        return False


def wait_after_submit(page: Page) -> None:
    try:
        page.wait_for_url("**/subpage/searchresult**", timeout=15000)
    except Exception:
        page.wait_for_load_state("domcontentloaded", timeout=10000)
        page.wait_for_timeout(3000)


def parse_cards_from_dom(page: Page) -> list[dict[str, Any]]:
    """Extract card groups from #zh-language-case / #pt-language-case containers."""
    script = r"""
    () => {
      const norm = (s) => (s || '').replace(/\s+/g, ' ').trim();
      const containers = Array.from(document.querySelectorAll('#zh-language-case, #pt-language-case'));
      const allCards = [];

      for (const container of containers) {
        const children = Array.from(container.children);
        for (let i = 0; i < children.length; i++) {
          const node = children[i];
          if (node.tagName !== 'LI') continue;
          if ((node.className || '').includes('seperate')) continue;

          const dateText = norm(node.querySelector('span.date')?.innerText || '');
          const caseNumberText = norm(node.querySelector('span.num')?.innerText || '');
          const typeText = norm(node.querySelector('span.type')?.innerText || '');
          const downloadNode = node.querySelector('span.download');

          const links = [];
          if (downloadNode) {
            const clickable = Array.from(downloadNode.querySelectorAll('a,button,span,i,img'));
            for (const el of clickable) {
              const href = el.getAttribute?.('href') || el.closest?.('a')?.getAttribute?.('href') || '';
              const onclick = el.getAttribute?.('onclick') || el.closest?.('a')?.getAttribute?.('onclick') || '';
              const cls = norm(el.className || el.closest?.('a')?.className || '');
              const text = norm(el.innerText || el.getAttribute?.('title') || el.getAttribute?.('aria-label') || '');
              const src = el.getAttribute?.('src') || '';
              links.push({ href, onclick, class_name: cls, text, src, outer_html: (el.outerHTML || '').slice(0, 300) });
            }
          }

          const detailBlocks = [];
          const rawParts = [norm(node.innerText || '')];

          let j = i + 1;
          while (j < children.length) {
            const next = children[j];
            if (next.tagName === 'LI') break;
            const txt = norm(next.innerText || '');
            if (txt) {
              rawParts.push(txt);
              const title = norm(next.querySelector('.case_tit')?.innerText || '');
              detailBlocks.push({ title, text: txt });
            }
            j += 1;
          }

          allCards.push({
            index: allCards.length,
            date_text: dateText,
            case_number_text: caseNumberText,
            case_type_text: typeText,
            links,
            detail_blocks: detailBlocks,
            raw_card_text: norm(rawParts.join(' ')),
          });
        }
      }

      return allCards;
    }
    """
    return page.evaluate(script)


def extract_labeled_value(text: str, keys: tuple[str, ...], stop_keys: tuple[str, ...] = ()) -> str | None:
    ntext = normalize_space(text)
    for key in keys:
        m = re.search(rf"{re.escape(key)}\s*[:：]?\s*(.+)", ntext, flags=re.IGNORECASE)
        if not m:
            continue
        value = m.group(1).strip()
        if stop_keys:
            cut_positions = []
            for sk in stop_keys:
                sm = re.search(rf"\s{re.escape(sk)}\s*[:：]?", value, flags=re.IGNORECASE)
                if sm:
                    cut_positions.append(sm.start())
            if cut_positions:
                value = value[: min(cut_positions)].strip()
        if value:
            return value
    return None


def resolve_text_action(card: dict[str, Any]) -> tuple[str | None, CandidateAction | None]:
    links = card.get("links") or []
    for idx, item in enumerate(links):
        href_raw = normalize_space(item.get("href"))
        onclick = normalize_space(item.get("onclick"))
        cls = normalize_space(item.get("class_name")).lower()
        text = normalize_space(item.get("text")).lower()
        src = normalize_space(item.get("src")).lower()
        combined = " ".join([href_raw.lower(), onclick.lower(), cls, text, src])

        is_text = any(k in combined for k in TEXT_KEYS) or bool(re.search(r"/sentence/(zh|pt)/\d+", href_raw))
        if not is_text:
            continue
        if href_raw.lower().endswith(".pdf"):
            continue

        action = CandidateAction(
            element_selector=f"span.download >> nth={idx}",
            href=urljoin(BASE_URL, href_raw) if href_raw else None,
            onclick=onclick or None,
            action_type="href" if href_raw else "onclick/js",
            label=text or cls or src,
        )
        descriptor = action.href or action.onclick or action.label
        return descriptor, action
    return None, None


def parse_refined_card(raw_card: dict[str, Any], court: str) -> dict[str, Any]:
    date_text = normalize_space(raw_card.get("date_text"))
    case_number_text = normalize_space(raw_card.get("case_number_text"))
    case_type_text = normalize_space(raw_card.get("case_type_text"))
    all_text = normalize_space(raw_card.get("raw_card_text"))

    decision_date_match = DATE_RE.search(date_text) or DATE_RE.search(all_text)
    case_number_match = CASE_NUMBER_RE.search(case_number_text) or CASE_NUMBER_RE.search(all_text)

    pdf_url = None
    for item in raw_card.get("links") or []:
        href = normalize_space(item.get("href"))
        if href and href.lower().endswith(".pdf"):
            pdf_url = urljoin(BASE_URL, href)
            break

    text_descriptor, _ = resolve_text_action(raw_card)

    subject = None
    summary = None
    decision_result = None
    reporting_judge = None
    assistant_judges = None

    for block in raw_card.get("detail_blocks") or []:
        title = normalize_space(block.get("title")).lower()
        text = normalize_space(block.get("text"))

        if any(k.lower() in title for k in SUBJECT_KEYS) and not subject:
            subject = extract_labeled_value(text, SUBJECT_KEYS, stop_keys=SUMMARY_KEYS + RESULT_KEYS + REPORTING_KEYS + ASSISTANT_KEYS) or text

        if any(k.lower() in title for k in SUMMARY_KEYS) and not summary:
            summary = extract_labeled_value(text, SUMMARY_KEYS, stop_keys=RESULT_KEYS + REPORTING_KEYS + ASSISTANT_KEYS) or text

        if not decision_result:
            decision_result = extract_labeled_value(text, RESULT_KEYS, stop_keys=REPORTING_KEYS + ASSISTANT_KEYS)
        if not reporting_judge:
            reporting_judge = extract_labeled_value(text, REPORTING_KEYS, stop_keys=ASSISTANT_KEYS)
        if not assistant_judges:
            assistant_judges = extract_labeled_value(text, ASSISTANT_KEYS)

    decision_result = decision_result or extract_labeled_value(all_text, RESULT_KEYS, stop_keys=REPORTING_KEYS + ASSISTANT_KEYS)
    reporting_judge = reporting_judge or extract_labeled_value(all_text, REPORTING_KEYS, stop_keys=ASSISTANT_KEYS)
    assistant_judges = assistant_judges or extract_labeled_value(all_text, ASSISTANT_KEYS)

    return {
        "court": court,
        "decision_date": decision_date_match.group(0) if decision_date_match else None,
        "case_number": case_number_match.group(0) if case_number_match else None,
        "case_type": case_type_text or None,
        "pdf_url": pdf_url,
        "text_url_or_action": text_descriptor,
        "subject": subject,
        "summary": summary,
        "decision_result": decision_result,
        "reporting_judge": reporting_judge,
        "assistant_judges": assistant_judges,
        "raw_card_text": all_text or None,
    }


def extract_fulltext_from_page(page: Page) -> str:
    selectors = ["#content", ".maincontent", ".case_summary", "article", "body"]
    for sel in selectors:
        try:
            txt = normalize_space(page.locator(sel).first.inner_text(timeout=2500))
            if len(txt) > 200:
                return txt
        except Exception:
            continue
    return normalize_space(page.inner_text("body"))


def click_and_extract_text_detail(context: BrowserContext, page: Page, card_index: int, card: dict[str, Any]) -> dict[str, Any] | None:
    # Build candidate selectors within this card row.
    candidates = page.locator("#zh-language-case li:not(.seperate), #pt-language-case li:not(.seperate)").nth(card_index).locator(
        "span.download a, span.download button, span.download img, span.download span, span.download i"
    )

    count = candidates.count()
    for i in range(count):
        node = candidates.nth(i)
        try:
            href = normalize_space(node.get_attribute("href") or "")
            onclick = normalize_space(node.get_attribute("onclick") or "")
            cls = normalize_space(node.get_attribute("class") or "")
            src = normalize_space(node.get_attribute("src") or "")
            text = normalize_space(node.inner_text() if node.inner_text() else "")
        except Exception:
            continue

        anchor = node.locator("xpath=ancestor-or-self::a[1]").first
        try:
            a_href = normalize_space(anchor.get_attribute("href") or "")
            a_onclick = normalize_space(anchor.get_attribute("onclick") or "")
            a_cls = normalize_space(anchor.get_attribute("class") or "")
        except Exception:
            a_href = ""
            a_onclick = ""
            a_cls = ""

        combined = " ".join([href, onclick, cls, src, text, a_href, a_onclick, a_cls]).lower()
        if ".pdf" in combined:
            continue

        looks_text_action = any(k in combined for k in TEXT_KEYS) or bool(re.search(r"/sentence/(zh|pt)/\d+", combined))
        if not looks_text_action:
            continue

        action_desc = a_href or href or a_onclick or onclick or text or cls or src

        popup_page = None
        try:
            with page.expect_popup(timeout=5000) as popup_info:
                node.click(timeout=5000, force=True)
            popup_page = popup_info.value
        except TimeoutError:
            try:
                node.click(timeout=5000, force=True)
            except Exception:
                continue

        detail_page = popup_page
        if detail_page is None:
            # Could be same tab, modal, or newly opened page not caught by popup.
            pages_after = context.pages
            if len(pages_after) >= 2:
                detail_page = pages_after[-1]
            else:
                detail_page = page

        try:
            detail_page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception:
            pass
        detail_page.wait_for_timeout(1000)

        # Handle potential overlay/dialog.
        overlay_text = ""
        for sel in [".fancybox-inner", ".mfp-content", ".modal-body", ".ui-dialog-content"]:
            try:
                loc = detail_page.locator(sel)
                if loc.count() > 0 and loc.first.is_visible():
                    overlay_text = normalize_space(loc.first.inner_text(timeout=2000))
                    if len(overlay_text) > 200:
                        break
            except Exception:
                continue

        full_text = overlay_text or extract_fulltext_from_page(detail_page)
        current_url = detail_page.url

        # Close popup if it was a new tab.
        if popup_page is not None:
            try:
                popup_page.close()
            except Exception:
                pass

        if len(full_text) < 200:
            continue

        return {
            "case_number": card.get("case_number"),
            "decision_date": card.get("decision_date"),
            "title_or_issue": card.get("subject") or card.get("case_type"),
            "full_text": full_text,
            "source_type": "txt/fulltext",
            "extracted_from": current_url if current_url and current_url != "about:blank" else action_desc,
        }

    return None


def hit_count(cards: list[dict[str, Any]], field: str) -> int:
    return sum(1 for c in cards if c.get(field))


def main() -> int:
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    selected_court = "unknown"
    raw_cards: list[dict[str, Any]] = []
    refined_cards: list[dict[str, Any]] = []
    text_samples: list[dict[str, Any]] = []

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(locale="zh-HK")
            page = context.new_page()

            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=45000)
            page.wait_for_timeout(2000)

            if not fill_recent_30_days(page):
                raise RuntimeError("failed to fill recent-30-days filters")

            selected_court = try_select_intermediate_court(page)
            if not click_search(page):
                raise RuntimeError("failed to submit search")

            wait_after_submit(page)
            RAW_RESULT_HTML_PATH.write_text(page.content(), encoding="utf-8")

            raw_cards = parse_cards_from_dom(page)
            refined_cards = [parse_refined_card(c, court=selected_court) for c in raw_cards]

            # Extract text-detail samples from first 1~3 cards with resolved text entry.
            sample_target = min(3, len(refined_cards))
            for i in range(sample_target):
                if not refined_cards[i].get("text_url_or_action"):
                    continue
                sample = click_and_extract_text_detail(context, page, i, refined_cards[i])
                if sample:
                    text_samples.append(sample)
                if len(text_samples) >= 3:
                    break

            browser.close()

    except Exception as exc:
        print(f"Day11 extractor failed: {exc}")
        return 1

    REFINED_CARDS_PATH.write_text(json.dumps(refined_cards, ensure_ascii=False, indent=2), encoding="utf-8")
    TEXT_SAMPLES_PATH.write_text(json.dumps(text_samples, ensure_ascii=False, indent=2), encoding="utf-8")

    corrected_case_number_hits = hit_count(refined_cards, "case_number")
    corrected_case_type_hits = hit_count(refined_cards, "case_type")
    text_entry_resolved_hits = hit_count(refined_cards, "text_url_or_action")
    sample_hits = len(text_samples)
    txt_success = sample_hits > 0 and all(s.get("source_type") == "txt/fulltext" for s in text_samples)

    report_lines = [
        "# Day 11 Playwright text-detail report",
        f"target_url: {TARGET_URL}",
        f"selected_court: {selected_court}",
        f"total cards parsed: {len(refined_cards)}",
        f"corrected case_number hit count: {corrected_case_number_hits}",
        f"corrected case_type hit count: {corrected_case_type_hits}",
        f"text entry resolved count: {text_entry_resolved_hits}",
        f"sample text details extracted count: {sample_hits}",
        f"txt/fulltext extraction appears successful: {txt_success}",
        "",
        "sample text details:",
        json.dumps(text_samples[:3], ensure_ascii=False, indent=2),
    ]
    REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"total cards parsed: {len(refined_cards)}")
    print(f"corrected case_number hit count: {corrected_case_number_hits}")
    print(f"corrected case_type hit count: {corrected_case_type_hits}")
    print(f"text entry resolved count: {text_entry_resolved_hits}")
    print(f"sample text details extracted count: {sample_hits}")
    print(f"whether txt/fulltext extraction appears successful: {txt_success}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
