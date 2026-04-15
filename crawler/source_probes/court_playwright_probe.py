"""Day 6 probe: verify Macau Courts judgment search browser interaction flow.

This script is intentionally a probe (not a production crawler):
- open search page in a real browser (Playwright)
- perform minimal interaction (date range + submit)
- capture navigation and network behavior
- persist artifacts for manual inspection
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from playwright.sync_api import BrowserContext, Page, Request, TimeoutError, sync_playwright

TARGET_URL = "https://www.court.gov.mo/zh/subpage/researchjudgments"
OUTPUT_DIR = Path("data/raw/court_probe")
BEFORE_HTML_PATH = OUTPUT_DIR / "playwright_before_submit.html"
AFTER_HTML_PATH = OUTPUT_DIR / "playwright_after_submit.html"
AFTER_SCREENSHOT_PATH = OUTPUT_DIR / "playwright_after_submit.png"
NETWORK_LOG_PATH = OUTPUT_DIR / "playwright_network_log.json"
REPORT_PATH = OUTPUT_DIR / "playwright_probe_report.txt"


@dataclass
class NetworkRecord:
    event: str
    url: str
    method: str
    resource_type: str
    post_data: str | None = None
    status: int | None = None
    failure_text: str | None = None


def find_date_inputs(page: Page) -> list[Any]:
    """Find likely date inputs using multiple fallback strategies."""
    selectors = [
        "input[type='date']",
        "input[name*='date' i]",
        "input[name*='日期']",
        "input[id*='date' i]",
        "input[id*='日期']",
        "input[placeholder*='日期']",
        "input[placeholder*='date' i]",
    ]

    found = []
    for selector in selectors:
        loc = page.locator(selector)
        for idx in range(min(loc.count(), 6)):
            handle = loc.nth(idx)
            if handle not in found:
                found.append(handle)

    return found


def fill_recent_30_days(page: Page) -> bool:
    """Fill minimal required date range fields.

    Returns True if at least one field was filled.
    """
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    candidates = find_date_inputs(page)
    if not candidates:
        return False

    filled_count = 0
    for idx, locator in enumerate(candidates[:2]):
        value = start_date.isoformat() if idx == 0 else end_date.isoformat()
        try:
            locator.click(timeout=3_000)
            locator.fill(value, timeout=3_000)
            filled_count += 1
        except Exception:
            continue

    return filled_count > 0


def click_search(page: Page) -> bool:
    """Click likely search button with robust fallbacks."""
    search_labels = ["搜尋", "搜索", "Search", "查詢"]

    for label in search_labels:
        button = page.get_by_role("button", name=label)
        if button.count() > 0:
            try:
                button.first.click(timeout=5_000)
                return True
            except Exception:
                pass

    fallback_selectors = [
        "button:has-text('搜尋')",
        "button:has-text('搜索')",
        "button:has-text('Search')",
        "input[type='submit']",
        "button[type='submit']",
    ]
    for selector in fallback_selectors:
        btn = page.locator(selector)
        if btn.count() > 0:
            try:
                btn.first.click(timeout=5_000)
                return True
            except Exception:
                continue

    return False


def contains_result_markers(html: str) -> bool:
    markers = ["案件", "裁判書", "結果", "result", "pagination", "page-item", "table"]
    return any(marker.lower() in html.lower() for marker in markers)


def likely_submission_request(records: list[NetworkRecord]) -> NetworkRecord | None:
    keywords = ["search", "judgment", "research", "query", "filter", "result"]

    # Prefer POST with meaningful payload
    for r in records:
        if r.method.upper() == "POST" and r.post_data:
            return r

    for r in records:
        url_lower = r.url.lower()
        if any(k in url_lower for k in keywords):
            return r

    return None


def attach_network_logging(context: BrowserContext, records: list[NetworkRecord]) -> None:
    def on_request(req: Request) -> None:
        post_data = None
        try:
            post_data = req.post_data
        except Exception:
            post_data = None

        records.append(
            NetworkRecord(
                event="request",
                url=req.url,
                method=req.method,
                resource_type=req.resource_type,
                post_data=post_data,
            )
        )

    def on_request_finished(req: Request) -> None:
        response = req.response()
        records.append(
            NetworkRecord(
                event="requestfinished",
                url=req.url,
                method=req.method,
                resource_type=req.resource_type,
                status=response.status if response else None,
            )
        )

    def on_request_failed(req: Request) -> None:
        failure = req.failure
        records.append(
            NetworkRecord(
                event="requestfailed",
                url=req.url,
                method=req.method,
                resource_type=req.resource_type,
                failure_text=failure if isinstance(failure, str) else str(failure),
            )
        )

    context.on("request", on_request)
    context.on("requestfinished", on_request_finished)
    context.on("requestfailed", on_request_failed)


def run_probe() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    network_records: list[NetworkRecord] = []
    navigation_events: list[str] = []
    submit_succeeded = False

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context(locale="zh-HK")
            page = context.new_page()

            attach_network_logging(context, network_records)
            page.on("framenavigated", lambda frame: navigation_events.append(frame.url))

            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=45_000)
            page.wait_for_timeout(2_000)
            page.wait_for_load_state("networkidle", timeout=20_000)

            BEFORE_HTML_PATH.write_text(page.content(), encoding="utf-8")

            filled_any_date = fill_recent_30_days(page)
            clicked = click_search(page)

            if clicked:
                submit_succeeded = True
                try:
                    page.wait_for_load_state("networkidle", timeout=20_000)
                except TimeoutError:
                    # Some flows keep polling; continue with captured state.
                    pass
                page.wait_for_timeout(2_000)

            AFTER_HTML_PATH.write_text(page.content(), encoding="utf-8")
            page.screenshot(path=str(AFTER_SCREENSHOT_PATH), full_page=True)

            final_url = page.url
            browser.close()

    except Exception as exc:
        print("Probe execution failed.")
        print(f"error: {exc}")
        return 1

    request_events = [r for r in network_records if r.event == "request"]
    search_candidate = likely_submission_request(request_events)

    after_html = AFTER_HTML_PATH.read_text(encoding="utf-8") if AFTER_HTML_PATH.exists() else ""
    has_result_markers = contains_result_markers(after_html)

    NETWORK_LOG_PATH.write_text(
        json.dumps(
            {
                "navigation_events": navigation_events,
                "network_records": [asdict(r) for r in network_records],
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    replay_feasible = bool(search_candidate and (search_candidate.method == "POST" or search_candidate.post_data))

    report_lines = [
        "Day 6 Playwright Probe Report",
        f"target_url: {TARGET_URL}",
        f"browser_submit_succeeded: {submit_succeeded}",
        f"final_page_url_after_submit: {final_url}",
        f"contains_apparent_result_markers: {has_result_markers}",
        f"date_fields_filled: {'YES' if 'filled_any_date' in locals() and filled_any_date else 'NO'}",
        f"total_captured_network_requests: {len(request_events)}",
        f"likely_search_submission_captured: {'YES' if search_candidate else 'NO'}",
        f"requests_replay_feasible_now: {'YES' if replay_feasible else 'NO'}",
    ]

    if search_candidate:
        report_lines.extend(
            [
                "search_candidate:",
                f"  method: {search_candidate.method}",
                f"  url: {search_candidate.url}",
                f"  has_post_data: {'YES' if bool(search_candidate.post_data) else 'NO'}",
                f"  post_data_preview: {(search_candidate.post_data or '')[:500]}",
            ]
        )

    REPORT_PATH.write_text("\n".join(report_lines) + "\n", encoding="utf-8")

    print(f"browser_submit_succeeded: {submit_succeeded}")
    print(f"current_page_url_after_submit: {final_url}")
    print(f"contains_apparent_result_rows_or_markers: {has_result_markers}")
    print(f"total_captured_network_requests: {len(request_events)}")
    print(f"likely_search_submission_request_captured: {bool(search_candidate)}")
    print(f"requests_replay_now_looks_feasible: {replay_feasible}")
    print(f"saved_before_html: {BEFORE_HTML_PATH}")
    print(f"saved_after_html: {AFTER_HTML_PATH}")
    print(f"saved_after_screenshot: {AFTER_SCREENSHOT_PATH}")
    print(f"saved_network_log: {NETWORK_LOG_PATH}")
    print(f"saved_report: {REPORT_PATH}")

    return 0


def main() -> None:
    raise SystemExit(run_probe())


if __name__ == "__main__":
    main()
