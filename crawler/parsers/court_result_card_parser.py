"""Day 9: deterministic parser for Macau Courts judgment result cards.

Scope:
- parse requests replay post-submit HTML only
- BeautifulSoup-based card extraction (no generic exploratory scanning)
- no Playwright
- no pagination
- no detail-page parsing
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

try:
    from bs4 import BeautifulSoup
    from bs4.element import Tag
except ModuleNotFoundError:  # pragma: no cover
    BeautifulSoup = None  # type: ignore[assignment]
    Tag = object  # type: ignore[assignment]

INPUT_HTML_PATH = Path("data/raw/court_probe/requests_replay_after_submit.html")
OUTPUT_DIR = Path("data/parsed/court_probe")
OUTPUT_JSON_PATH = OUTPUT_DIR / "requests_result_cards.json"
OUTPUT_REPORT_PATH = OUTPUT_DIR / "requests_result_cards_report.txt"
BASE_URL = "https://www.court.gov.mo"

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


def label_signature(tag: Tag) -> str:
    classes = ".".join(sorted(tag.get("class", [])))
    if classes:
        return f"{tag.name}|{classes}"
    return tag.name


def card_quality_score(tag: Tag) -> int:
    text = normalize_space(tag.get_text(" ", strip=True))
    anchors = tag.find_all("a", href=True)
    score = 0

    if DATE_RE.search(text):
        score += 1
    if CASE_RE.search(text):
        score += 1
    if has_any(text, SUBJECT_KEYS):
        score += 1
    if has_any(text, SUMMARY_KEYS):
        score += 1
    if has_any(text, DECISION_RESULT_KEYS):
        score += 1

    for a in anchors:
        href = (a.get("href") or "").lower()
        a_text = normalize_space(a.get_text(" ", strip=True)).lower()
        if any(k in href or k in a_text for k in PDF_LINK_KEYS):
            score += 1
            break
    for a in anchors:
        href = (a.get("href") or "").lower()
        a_text = normalize_space(a.get_text(" ", strip=True)).lower()
        if any(k in href or k in a_text for k in TEXT_LINK_KEYS):
            score += 1
            break

    return score


def find_repeated_card_containers(soup: BeautifulSoup) -> list[Tag]:
    # Deterministic strategy: repeated containers only, then keep high-quality cards.
    pool = soup.find_all(["div", "li", "article", "section"])
    sig_counts = Counter(label_signature(tag) for tag in pool)

    repeated = [tag for tag in pool if sig_counts[label_signature(tag)] >= 3]
    scored = [(card_quality_score(tag), tag) for tag in repeated]
    scored = [it for it in scored if it[0] >= 4]

    # Remove parent wrappers when a better-scored child is also selected.
    selected: list[Tag] = []
    selected_ids = {id(tag) for _, tag in scored}
    for _, tag in sorted(scored, key=lambda x: x[0], reverse=True):
        if any(id(child) in selected_ids for child in tag.find_all(["div", "li", "article", "section"])):
            # If it wraps another selected block, skip the wrapper.
            if any(id(child) != id(tag) and id(child) in selected_ids for child in tag.find_all(["div", "li", "article", "section"])):
                continue
        selected.append(tag)

    # Stable order by appearance and dedupe.
    seen: set[int] = set()
    out: list[Tag] = []
    for tag in repeated:
        if id(tag) in seen:
            continue
        if any(id(tag) == id(sel) for sel in selected):
            seen.add(id(tag))
            out.append(tag)
    return out


def extract_field_by_label(text: str, keys: tuple[str, ...]) -> str | None:
    for key in keys:
        pattern = re.compile(rf"{re.escape(key)}\s*[:：]?\s*([^\n\r]+)", re.IGNORECASE)
        m = pattern.search(text)
        if m:
            value = normalize_space(m.group(1))
            if value:
                return value
    return None


def extract_links(card: Tag) -> tuple[str | None, str | None]:
    pdf_url = None
    text_url = None

    for a in card.find_all("a", href=True):
        href_raw = a.get("href") or ""
        href = urljoin(BASE_URL, href_raw)
        href_l = href.lower()
        label = normalize_space(a.get_text(" ", strip=True)).lower()

        if pdf_url is None and any(k in href_l or k in label for k in PDF_LINK_KEYS):
            pdf_url = href
            continue

        if text_url is None and any(k in href_l or k in label for k in TEXT_LINK_KEYS):
            text_url = href

    return pdf_url, text_url


def infer_court(page_text: str) -> str:
    if "中級法院" in page_text or "tribunal de segunda" in page_text.lower():
        return "中級法院"
    if "終審法院" in page_text or "tribunal de última instância" in page_text.lower():
        return "終審法院"
    if "初級法院" in page_text or "tribunal judicial de base" in page_text.lower():
        return "初級法院"
    return "unknown"


def parse_card(card: Tag, court: str) -> dict[str, Any]:
    raw_text = normalize_space(card.get_text(" ", strip=True))
    decision_date_match = DATE_RE.search(raw_text)
    case_number_match = CASE_RE.search(raw_text)

    # Case type heuristic: top-line chunks around date/case number.
    case_type = None
    top_line = normalize_space(card.get_text(" ", strip=True))
    if case_number_match:
        suffix = top_line[case_number_match.end() :]
        suffix = normalize_space(suffix)
        if suffix:
            case_type = suffix.split(" ")[0]

    subject = extract_field_by_label(raw_text, SUBJECT_KEYS)
    summary = extract_field_by_label(raw_text, SUMMARY_KEYS)
    decision_result = extract_field_by_label(raw_text, DECISION_RESULT_KEYS)
    reporting_judge = extract_field_by_label(raw_text, REPORTING_JUDGE_KEYS)
    assistant_judges = extract_field_by_label(raw_text, ASSISTANT_JUDGE_KEYS)
    pdf_url, text_url = extract_links(card)

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
    return sum(1 for card in cards if card.get(field))


def looks_like_true_judgment_cards(cards: list[dict[str, Any]]) -> bool:
    if not cards:
        return False
    must_have_case = hit_count(cards, "case_number") / len(cards)
    must_have_date = hit_count(cards, "decision_date") / len(cards)
    must_have_doc = sum(1 for c in cards if c.get("pdf_url") or c.get("text_url")) / len(cards)
    return must_have_case >= 0.6 and must_have_date >= 0.6 and must_have_doc >= 0.6


def build_report(total_detected: int, cards: list[dict[str, Any]], looks_true: bool) -> str:
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
        "# Court deterministic result-card parser report (Day 9)",
        f"input_html: {INPUT_HTML_PATH}",
        f"output_json: {OUTPUT_JSON_PATH}",
        "",
        f"total cards detected: {total_detected}",
        f"total cards parsed: {len(cards)}",
    ]

    for field in fields:
        lines.append(f"hit count - {field}: {hit_count(cards, field)}")

    lines.extend(
        [
            "",
            f"looks_like_true_judgment_cards: {looks_true}",
            "",
            "sample cards (first 3):",
        ]
    )
    for idx, card in enumerate(cards[:3], start=1):
        lines.append(f"- card {idx}: {json.dumps(card, ensure_ascii=False)}")
    if not cards:
        lines.append("- (none)")
    return "\n".join(lines)


def run() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if BeautifulSoup is None:
        OUTPUT_JSON_PATH.write_text("[]\n", encoding="utf-8")
        OUTPUT_REPORT_PATH.write_text(
            "# Court deterministic result-card parser report (Day 9)\n"
            "error: missing dependency bs4 (BeautifulSoup).\n",
            encoding="utf-8",
        )
        print("total cards detected: 0")
        print("total cards parsed: 0")
        print("hit count - decision_date: 0")
        print("hit count - case_number: 0")
        print("hit count - pdf_url: 0")
        print("hit count - text_url: 0")
        print("whether output looks like true judgment cards: False")
        print("error: missing dependency bs4 (BeautifulSoup)")
        return 3

    if not INPUT_HTML_PATH.exists():
        OUTPUT_JSON_PATH.write_text("[]\n", encoding="utf-8")
        OUTPUT_REPORT_PATH.write_text(
            "# Court deterministic result-card parser report (Day 9)\n"
            f"error: input html file not found: {INPUT_HTML_PATH}\n",
            encoding="utf-8",
        )
        print("total cards detected: 0")
        print("total cards parsed: 0")
        print("hit count - decision_date: 0")
        print("hit count - case_number: 0")
        print("hit count - pdf_url: 0")
        print("hit count - text_url: 0")
        print("whether output looks like true judgment cards: False")
        print(f"error: input html file not found at {INPUT_HTML_PATH}")
        return 1

    try:
        html = INPUT_HTML_PATH.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        html = INPUT_HTML_PATH.read_text(encoding="big5", errors="ignore")
    except OSError as exc:
        OUTPUT_JSON_PATH.write_text("[]\n", encoding="utf-8")
        OUTPUT_REPORT_PATH.write_text(
            "# Court deterministic result-card parser report (Day 9)\n"
            f"error: failed reading html: {exc}\n",
            encoding="utf-8",
        )
        print("total cards detected: 0")
        print("total cards parsed: 0")
        print("hit count - decision_date: 0")
        print("hit count - case_number: 0")
        print("hit count - pdf_url: 0")
        print("hit count - text_url: 0")
        print("whether output looks like true judgment cards: False")
        print(f"error: failed reading input html: {exc}")
        return 2

    soup = BeautifulSoup(html, "html.parser")
    page_text = normalize_space(soup.get_text(" ", strip=True))
    inferred_court = infer_court(page_text)

    card_tags = find_repeated_card_containers(soup)
    parsed_cards = [parse_card(tag, court=inferred_court) for tag in card_tags]
    parsed_cards = [c for c in parsed_cards if c.get("raw_card_text")]
    parsed_cards = dedupe_cards(parsed_cards)

    looks_true = looks_like_true_judgment_cards(parsed_cards)

    OUTPUT_JSON_PATH.write_text(
        json.dumps(parsed_cards, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    OUTPUT_REPORT_PATH.write_text(
        build_report(total_detected=len(card_tags), cards=parsed_cards, looks_true=looks_true) + "\n",
        encoding="utf-8",
    )

    print(f"total cards detected: {len(card_tags)}")
    print(f"total cards parsed: {len(parsed_cards)}")
    print(f"hit count - decision_date: {hit_count(parsed_cards, 'decision_date')}")
    print(f"hit count - case_number: {hit_count(parsed_cards, 'case_number')}")
    print(f"hit count - pdf_url: {hit_count(parsed_cards, 'pdf_url')}")
    print(f"hit count - text_url: {hit_count(parsed_cards, 'text_url')}")
    print(f"whether output looks like true judgment cards: {looks_true}")
    print(f"saved_json: {OUTPUT_JSON_PATH}")
    print(f"saved_report: {OUTPUT_REPORT_PATH}")
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
