"""Day 7 probe: replay browser-captured Macau Courts request with requests.

Scope:
- requests + BeautifulSoup only
- refresh session/token via preflight GET
- replay captured POST fields from Day 6 network understanding
- persist post-submit artifact + plain-text report

Out of scope:
- Playwright
- DB integration
- full crawler pipeline
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

TARGET_PATH = "/zh/subpage/researchjudgments"
TARGET_URL = f"https://www.court.gov.mo{TARGET_PATH}?court=tui"
OUTPUT_DIR = Path("data/raw/court_probe")
AFTER_SUBMIT_HTML_PATH = OUTPUT_DIR / "requests_replay_after_submit.html"
REPORT_PATH = OUTPUT_DIR / "requests_replay_report.txt"

SEARCH_FORM_MARKERS: tuple[str, ...] = (
    "裁判書搜尋",
    "宣判日期",
    "案件編號",
    "法院",
    "種類",
    "查詢",
)

CANDIDATE_CASE_MARKERS: tuple[str, ...] = (
    "案件",
    "裁判書",
    "編號",
    "判決",
    "上訴",
    "結果",
    "下載",
)


def detect_search_form(html: str) -> tuple[bool, int]:
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    marker_hits = sum(1 for m in SEARCH_FORM_MARKERS if m in text)
    has_form = "<form" in html.lower()
    return has_form and marker_hits >= 3, marker_hits


def detect_candidate_markers(html: str) -> tuple[bool, int]:
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    marker_hits = sum(1 for m in CANDIDATE_CASE_MARKERS if m in text)
    return marker_hits >= 3, marker_hits


def extract_token(html: str) -> str | None:
    soup = BeautifulSoup(html, "html.parser")

    # Prefer exact Day-6-captured style field name.
    direct = soup.find("input", attrs={"name": "wizcasesearch_sentence_filter_type[_token]"})
    if direct and direct.get("value"):
        return str(direct["value"])

    # Fallback: any hidden token-like field in this form.
    token_input = soup.find("input", attrs={"name": lambda n: isinstance(n, str) and "_token" in n})
    if token_input and token_input.get("value"):
        return str(token_input["value"])

    return None


def build_payload(token: str) -> dict[str, str]:
    today = date.today()
    start_day = today - timedelta(days=30)

    return {
        "wizcasesearch_sentence_filter_type[court]": "tui",
        "wizcasesearch_sentence_filter_type[decisionDate][left_date]": start_day.isoformat(),
        "wizcasesearch_sentence_filter_type[decisionDate][right_date]": today.isoformat(),
        "wizcasesearch_sentence_filter_type[recContent][logic]": "and",
        "wizcasesearch_sentence_filter_type[recContent][key][]": "",
        "wizcasesearch_sentence_filter_type[_token]": token,
    }


def resolve_post_url(preflight_html: str, base_url: str) -> str:
    soup = BeautifulSoup(preflight_html, "html.parser")
    form = soup.find("form")
    action = form.get("action") if form else None
    if isinstance(action, str) and action.strip():
        return urljoin(base_url, action)
    return TARGET_URL


def run_probe() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        }
    )

    try:
        preflight = session.get(TARGET_URL, timeout=30)
    except requests.RequestException as exc:
        print(f"preflight GET failed: {exc}")
        return 1

    print(f"preflight GET status: {preflight.status_code}")

    if preflight.status_code != 200:
        print("preflight GET did not return HTTP 200")
        return 2

    token = extract_token(preflight.text)
    if not token:
        print("could not extract CSRF token from preflight page")
        return 3

    post_url = resolve_post_url(preflight.text, preflight.url)
    payload = build_payload(token)

    headers = {
        "Referer": preflight.url,
        "Content-Type": "application/x-www-form-urlencoded",
    }

    try:
        post_resp = session.post(post_url, data=payload, headers=headers, timeout=45)
    except requests.RequestException as exc:
        print(f"POST replay failed: {exc}")
        return 4

    html = post_resp.text
    looks_like_search_form, search_hits = detect_search_form(html)
    has_case_markers, case_hits = detect_candidate_markers(html)
    appears_successful = post_resp.status_code == 200 and has_case_markers and not looks_like_search_form

    try:
        AFTER_SUBMIT_HTML_PATH.write_text(html, encoding=post_resp.encoding or "utf-8")
    except OSError as exc:
        print(f"failed to write HTML artifact: {exc}")
        return 5

    report_lines = [
        "Day 7 requests replay probe report",
        f"preflight_get_status: {preflight.status_code}",
        f"post_status: {post_resp.status_code}",
        f"post_url_used: {post_url}",
        f"final_url: {post_resp.url}",
        f"response_length: {len(html)}",
        f"looks_like_search_form: {looks_like_search_form}",
        f"search_form_marker_hits: {search_hits}",
        f"contains_candidate_case_markers: {has_case_markers}",
        f"candidate_case_marker_hits: {case_hits}",
        f"replay_appears_successful: {appears_successful}",
    ]

    try:
        REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    except OSError as exc:
        print(f"failed to write report artifact: {exc}")
        return 6

    print(f"POST status: {post_resp.status_code}")
    print(f"final URL: {post_resp.url}")
    print(f"response length: {len(html)}")
    print(f"whether page still looks like search form: {looks_like_search_form}")
    print(f"whether page contains candidate case markers: {has_case_markers}")
    print(f"whether replay appears successful: {appears_successful}")
    print(f"saved_html: {AFTER_SUBMIT_HTML_PATH}")
    print(f"saved_report: {REPORT_PATH}")

    return 0


def main() -> None:
    raise SystemExit(run_probe())


if __name__ == "__main__":
    main()
