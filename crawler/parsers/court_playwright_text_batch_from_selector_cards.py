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
INPUT_CARDS_PATH = PARSED_DIR / "playwright_result_cards_selector_driven.json"
OUTPUT_JSONL_PATH = PARSED_DIR / "playwright_text_details_from_selector_cards.jsonl"
OUTPUT_REPORT_PATH = PARSED_DIR / "playwright_text_details_from_selector_cards_report.txt"

MIN_FULLTEXT_CHARS = 200
PLAYWRIGHT_ERROR = Exception


def load_playwright():
    try:
        from playwright.sync_api import Error as PlaywrightError  # type: ignore
        from playwright.sync_api import sync_playwright  # type: ignore
    except ModuleNotFoundError:
        return None, None
    return PlaywrightError, sync_playwright


def normalize_space(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def normalize_multiline_text(value: str | None) -> str:
    if not value:
        return ""

    text = (value or "").replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    text = text.replace("\ufeff", "")

    normalized_lines: list[str] = []
    for line in text.split("\n"):
        cleaned = re.sub(r"[\t\f\v ]+", " ", line).strip()
        normalized_lines.append(cleaned)

    out_lines: list[str] = []
    blank_open = False
    for line in normalized_lines:
        if not line:
            if not blank_open:
                out_lines.append("")
                blank_open = True
            continue
        out_lines.append(line)
        blank_open = False

    return "\n".join(out_lines).strip()


def detect_language_from_url(url: str | None) -> str:
    lower = (url or "").lower()
    if "/zh/" in lower:
        return "zh"
    if "/pt/" in lower:
        return "pt"
    return "unknown"


def extract_body_first_text(page: "Page") -> str:
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

        const hasPrintText =
          text.includes('打印全文') ||
          text.includes('列印全文') ||
          text.toLowerCase() === 'print' ||
          text.toLowerCase().includes('imprimir');

        const printLike =
          onclick.includes('window.print') ||
          style.includes('float: right');

        if (hasPrintText && (printLike || tag === 'a' || tag === 'div')) {
          el.remove();
          continue;
        }

        if (tag === 'a' && (onclick.includes('window.print') || hasPrintText)) {
          el.remove();
        }
      }

      const raw = (clone.innerText || clone.textContent || '').trim();
      return raw;
    }
    """

    try:
        return str(page.evaluate(script) or "")
    except PLAYWRIGHT_ERROR:
        return page.inner_text("body")


def remove_print_noise_from_text(text: str) -> str:
    if not text:
        return ""

    bad_line_patterns = [
        r"^打印全文$",
        r"^列印全文$",
        r"^print$",
        r"^imprimir(?:\s+texto\s+integral)?$",
    ]
    compiled = [re.compile(p, flags=re.IGNORECASE) for p in bad_line_patterns]

    cleaned_lines: list[str] = []
    for line in text.split("\n"):
        stripped = line.strip()
        if stripped and any(p.match(stripped) for p in compiled):
            continue
        cleaned_lines.append(line)

    return "\n".join(cleaned_lines)


def get_non_empty_lines(text: str, limit: int | None = None) -> list[str]:
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if limit is not None:
        return lines[:limit]
    return lines


def parse_detail_case_number(text: str) -> str | None:
    lines = get_non_empty_lines(text, limit=20)

    patterns = [
        r"(?:案件編號|卷宗編號|編號|案號)\s*[:：]?\s*(?:第)?\s*([0-9]{1,6}/[0-9]{4})\s*號?",
        r"^第\s*([0-9]{1,6}/[0-9]{4})\s*號(?:.*案)?$",
        r"\b([0-9]{1,6}/[0-9]{4})\b",
    ]

    for line in lines:
        for pattern in patterns:
            m = re.search(pattern, line)
            if m:
                return normalize_space(m.group(1)) or None

    return None


def parse_detail_decision_date(text: str) -> str | None:
    lines = get_non_empty_lines(text, limit=20)

    patterns = [
        r"(?:裁判日期|判決日期|日期)\s*[:：]\s*([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日)",
        r"(?:裁判日期|判決日期|日期)\s*[:：]\s*([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})",
        r"\b([0-9]{4}年[0-9]{1,2}月[0-9]{1,2}日)\b",
        r"\b([0-9]{1,2}/[0-9]{1,2}/[0-9]{4})\b",
    ]

    for line in lines:
        for pattern in patterns:
            m = re.search(pattern, line)
            if m:
                return normalize_space(m.group(1)) or None

    return None


def looks_like_title_value(value: str) -> bool:
    v = normalize_space(value)
    if not v:
        return False
    if len(v) < 2 or len(v) > 120:
        return False
    if re.fullmatch(r"[0-9]{1,6}/[0-9]{4}", v):
        return False
    if "日期" in v:
        return False
    if "裁判書製作人" in v:
        return False
    if "澳門特別行政區" in v:
        return False
    return True


def parse_detail_title_or_issue(text: str) -> str | None:
    lines = get_non_empty_lines(text, limit=20)

    # 優先：前幾行中帶冒號的題名型欄位，但不把欄位名寫死到只剩單一格式
    # 這裡只排除明顯不是 title 的 key
    for line in lines:
        m = re.match(r"^([^:：]{1,20})\s*[:：]\s*(.+)$", line)
        if not m:
            continue

        key = normalize_space(m.group(1))
        value = normalize_space(m.group(2))

        if key in {
            "案件編號", "卷宗編號", "編號", "案號",
            "日期", "裁判日期", "判決日期",
            "上訴人", "主上訴人", "主被上訴人",
            "附帶上訴人", "附帶被上訴人",
            "聲請人", "被訴實體",
        }:
            continue

        if looks_like_title_value(value):
            return value

    # 次優先：前幾行中第一條看起來像短標題的行
    stop_tokens = (
        "摘要", "摘 要", "裁判摘要", "裁判書製作人",
        "一、案情敘述", "一、 案件概述", "澳門特別行政區"
    )
    for line in lines[:10]:
        if any(token == line or token in line for token in stop_tokens):
            break
        if looks_like_title_value(line) and not re.search(r"[0-9]{1,6}/[0-9]{4}", line):
            return line

    return None


def good_full_text(text: str) -> bool:
    text = text.strip()
    if not text:
        return False
    if len(text) < MIN_FULLTEXT_CHARS:
        return False
    if len(re.findall(r"\S+", text)) < 60:
        return False
    return True


def build_record(card: dict[str, Any], detail_url: str, full_text: str) -> dict[str, Any]:
    detail_case_number = parse_detail_case_number(full_text)
    detail_decision_date = parse_detail_decision_date(full_text)
    detail_title_or_issue = parse_detail_title_or_issue(full_text)

    return {
        "court": card.get("court"),
        "source_list_case_number": card.get("case_number"),
        "source_list_decision_date": card.get("decision_date"),
        "source_list_case_type": card.get("case_type"),
        "pdf_url": card.get("pdf_url"),
        "text_url_or_action": card.get("text_url_or_action"),
        "page_number": card.get("page_number"),
        "detail_case_number": detail_case_number,
        "detail_decision_date": detail_decision_date,
        "detail_title_or_issue": detail_title_or_issue,
        "language": detect_language_from_url(detail_url),
        "full_text": full_text,
        "detail_metadata_authoritative": bool(
            detail_case_number or detail_decision_date or detail_title_or_issue
        ),
        "extracted_from": detail_url,
    }


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def read_input_cards(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError("selector-driven cards input must be a JSON array")
    return [row for row in data if isinstance(row, dict)]


def main() -> int:
    if not INPUT_CARDS_PATH.exists():
        print(f"missing input file: {INPUT_CARDS_PATH}")
        return 1

    cards = read_input_cards(INPUT_CARDS_PATH)
    usable_cards = [c for c in cards if normalize_space(c.get("text_url_or_action"))]

    total_selector_cards = len(cards)
    cards_with_usable_text_url = len(usable_cards)
    attempted = cards_with_usable_text_url

    records: list[dict[str, Any]] = []
    failures: list[str] = []
    language_counts: Counter[str] = Counter()

    playwright_error, sync_playwright = load_playwright()
    global PLAYWRIGHT_ERROR

    if not sync_playwright:
        write_jsonl(OUTPUT_JSONL_PATH, [])
        appears_successful, _ = compute_extraction_success(
            attempted=attempted,
            successful=0,
            failed=attempted,
            non_empty_full_text_count=0,
        )
        report = [
            "# Day 18 batch text-detail extraction from selector-driven cards",
            f"input_cards_path: {INPUT_CARDS_PATH}",
            f"total selector cards read: {total_selector_cards}",
            f"cards with usable text_url_or_action: {cards_with_usable_text_url}",
            f"total detail pages attempted: {attempted}",
            "total detail pages succeeded: 0",
            f"total detail pages failed: {attempted}",
            "zh count: 0",
            "pt count: 0",
            "average full_text length: 0.00",
            f"whether batch extraction from selector-driven cards appears successful: {appears_successful}",
            "",
            "failures:",
            "- Playwright is not installed in this environment.",
        ]
        OUTPUT_REPORT_PATH.write_text("\n".join(report) + "\n", encoding="utf-8")

        print(f"total selector cards read: {total_selector_cards}")
        print(f"cards with usable text_url_or_action: {cards_with_usable_text_url}")
        print(f"total detail pages attempted: {attempted}")
        print("total detail pages succeeded: 0")
        print(f"total detail pages failed: {attempted}")
        print("zh count: 0")
        print("pt count: 0")
        print("average full_text length: 0.00")
        print(f"whether batch extraction from selector-driven cards appears successful: {appears_successful}")
        return 0 if appears_successful else 2

    PLAYWRIGHT_ERROR = playwright_error

    success_count = 0
    failed_count = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(locale="zh-HK")
        page = context.new_page()

        for idx, card in enumerate(usable_cards, start=1):
            target = normalize_space(card.get("text_url_or_action"))
            try:
                page.goto(target, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(800)

                body_raw = extract_body_first_text(page)
                normalized = normalize_multiline_text(remove_print_noise_from_text(body_raw))

                if not good_full_text(normalized):
                    raise RuntimeError("full_text failed minimum quality threshold")

                record = build_record(card, page.url, normalized)
                records.append(record)
                success_count += 1
                language_counts[record["language"]] += 1
                print(f"[{idx}] success: {target}")
            except Exception as exc:
                failed_count += 1
                failures.append(f"{target} | {exc}")
                print(f"[{idx}] failed: {target} | {exc}")

        browser.close()

    write_jsonl(OUTPUT_JSONL_PATH, records)

    non_empty_full_text_count = sum(1 for r in records if normalize_space(r.get("full_text")))
    appears_successful, _ = compute_extraction_success(
        attempted=attempted,
        successful=success_count,
        failed=failed_count,
        non_empty_full_text_count=non_empty_full_text_count,
    )

    avg_length = (
        sum(len(normalize_space(r.get("full_text"))) for r in records) / len(records)
        if records
        else 0.0
    )

    report_lines = [
        "# Day 18 batch text-detail extraction from selector-driven cards",
        f"input_cards_path: {INPUT_CARDS_PATH}",
        f"total selector cards read: {total_selector_cards}",
        f"cards with usable text_url_or_action: {cards_with_usable_text_url}",
        f"total detail pages attempted: {attempted}",
        f"total detail pages succeeded: {success_count}",
        f"total detail pages failed: {failed_count}",
        f"zh count: {language_counts.get('zh', 0)}",
        f"pt count: {language_counts.get('pt', 0)}",
        f"average full_text length: {avg_length:.2f}",
        f"whether batch extraction from selector-driven cards appears successful: {appears_successful}",
        "",
        "failures:",
        *([f"- {line}" for line in failures] or ["- none"]),
    ]
    OUTPUT_REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"total selector cards read: {total_selector_cards}")
    print(f"cards with usable text_url_or_action: {cards_with_usable_text_url}")
    print(f"total detail pages attempted: {attempted}")
    print(f"total detail pages succeeded: {success_count}")
    print(f"total detail pages failed: {failed_count}")
    print(f"zh count: {language_counts.get('zh', 0)}")
    print(f"pt count: {language_counts.get('pt', 0)}")
    print(f"average full_text length: {avg_length:.2f}")
    print(f"whether batch extraction from selector-driven cards appears successful: {appears_successful}")

    return 0 if appears_successful else 2


if __name__ == "__main__":
    raise SystemExit(main())