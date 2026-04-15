"""Day 3 form reverse-engineering probe for Macau Court judgment search.

Scope of this script (and only this scope):
- Load saved Day 2 HTML when available; otherwise refetch source page.
- Locate and inspect HTML form(s).
- Persist form structure summary for engineering review.
- Infer likely judgment-date-from/to fields.
- Attempt one minimal search request for the most recent 30 days.
- Persist search response HTML + plain text report.

Out of scope:
- Full crawler pipeline
- Browser automation
- Database integration
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup, Tag

TARGET_URL = "https://www.court.gov.mo/zh/subpage/researchjudgments"
OUTPUT_DIR = Path("data/raw/court_probe")
LOCAL_HTML_PATH = OUTPUT_DIR / "researchjudgments.html"
FORM_FIELDS_JSON_PATH = OUTPUT_DIR / "form_fields.json"
SEARCH_ATTEMPT_HTML_PATH = OUTPUT_DIR / "search_attempt_last_30_days.html"
SEARCH_ATTEMPT_REPORT_PATH = OUTPUT_DIR / "search_attempt_report.txt"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}


@dataclass
class SearchAttemptResult:
    attempted: bool
    status_code: int | None
    final_url: str | None
    response_length: int
    error: str | None = None


def ensure_html_source() -> tuple[str | None, str]:
    """Return page HTML and source mode ('local' or 'fetched')."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if LOCAL_HTML_PATH.exists():
        try:
            html = LOCAL_HTML_PATH.read_text(encoding="utf-8")
            return html, "local"
        except OSError as exc:
            print(f"Failed reading local HTML; will refetch. error: {exc}")

    try:
        response = requests.get(TARGET_URL, timeout=30, headers=REQUEST_HEADERS)
        response.raise_for_status()
    except requests.RequestException as exc:
        print("Failed to fetch source page.")
        print(f"error: {exc}")
        return None, "fetch_failed"

    html = response.text
    try:
        LOCAL_HTML_PATH.write_text(html, encoding=response.encoding or "utf-8")
    except OSError as exc:
        print(f"Warning: could not save refreshed HTML. error: {exc}")

    return html, "fetched"


def extract_fields(form: Tag) -> dict[str, Any]:
    """Extract input/select/textarea metadata from a form."""
    input_fields: list[dict[str, Any]] = []
    select_fields: list[dict[str, Any]] = []
    textarea_fields: list[dict[str, Any]] = []
    hidden_fields: list[dict[str, Any]] = []

    for inp in form.find_all("input"):
        item = {
            "name": inp.get("name"),
            "id": inp.get("id"),
            "type": inp.get("type", "text"),
            "value": inp.get("value"),
            "placeholder": inp.get("placeholder"),
        }
        input_fields.append(item)
        if (inp.get("type") or "").lower() == "hidden":
            hidden_fields.append(item)

    for sel in form.find_all("select"):
        options: list[dict[str, str | None]] = []
        for option in sel.find_all("option"):
            options.append(
                {
                    "value": option.get("value"),
                    "text": option.get_text(strip=True),
                }
            )
        select_fields.append(
            {
                "name": sel.get("name"),
                "id": sel.get("id"),
                "options": options,
            }
        )

    for ta in form.find_all("textarea"):
        textarea_fields.append(
            {
                "name": ta.get("name"),
                "id": ta.get("id"),
                "placeholder": ta.get("placeholder"),
                "value": ta.get_text(strip=True),
            }
        )

    return {
        "action": form.get("action"),
        "method": (form.get("method") or "get").lower(),
        "inputs": input_fields,
        "selects": select_fields,
        "textareas": textarea_fields,
        "hidden_fields": hidden_fields,
    }


def pick_target_form(forms: list[Tag]) -> tuple[int, Tag] | tuple[None, None]:
    """Pick likely judgment-search form with simple heuristic scoring."""
    if not forms:
        return None, None

    best_idx = 0
    best_score = -1
    keywords = ("宣判", "日期", "案件", "裁判", "search")

    for idx, form in enumerate(forms):
        text = form.get_text(" ", strip=True).lower()
        score = len(form.find_all("input")) + len(form.find_all("select"))
        for kw in keywords:
            if kw in text:
                score += 5
        if score > best_score:
            best_idx = idx
            best_score = score

    return best_idx, forms[best_idx]


def find_label_for_field(soup: BeautifulSoup, field_id: str | None) -> str | None:
    """Resolve corresponding <label> text when field id exists."""
    if not field_id:
        return None
    label = soup.find("label", attrs={"for": field_id})
    if isinstance(label, Tag):
        return label.get_text(" ", strip=True)
    return None


def guess_date_fields(soup: BeautifulSoup, form: Tag, field_summary: dict[str, Any]) -> dict[str, str | None]:
    """Infer likely judgment date range fields using names, ids, labels, placeholders."""
    from_field: str | None = None
    to_field: str | None = None

    candidates: list[dict[str, str | None]] = []
    for item in field_summary["inputs"] + field_summary["textareas"]:
        name = (item.get("name") or "")
        fid = (item.get("id") or "")
        placeholder = (item.get("placeholder") or "")
        label = find_label_for_field(soup, item.get("id")) or ""
        blob = " ".join([name, fid, placeholder, label]).lower()
        candidates.append({"name": item.get("name"), "blob": blob})

    from_markers = ("from", "start", "begin", "datefrom", "min", "起", "由")
    to_markers = ("to", "end", "until", "dateto", "max", "迄", "至")
    date_markers = ("date", "日期", "宣判", "judgment")

    for cand in candidates:
        blob = cand["blob"] or ""
        name = cand["name"]
        if not name:
            continue
        has_date_hint = any(marker in blob for marker in date_markers)
        if not has_date_hint:
            continue
        if from_field is None and any(marker in blob for marker in from_markers):
            from_field = name
        if to_field is None and any(marker in blob for marker in to_markers):
            to_field = name

    # Fallback: pick first 2 date-looking fields.
    if from_field is None or to_field is None:
        date_like = [
            cand["name"]
            for cand in candidates
            if cand["name"] and any(m in (cand["blob"] or "") for m in date_markers)
        ]
        if from_field is None and date_like:
            from_field = date_like[0]
        if to_field is None and len(date_like) > 1:
            to_field = date_like[1]

    return {"date_from": from_field, "date_to": to_field}


def build_min_payload(field_summary: dict[str, Any], guessed_dates: dict[str, str | None]) -> dict[str, str]:
    """Build a minimal payload using hidden defaults + guessed date window."""
    payload: dict[str, str] = {}

    for hidden in field_summary["hidden_fields"]:
        name = hidden.get("name")
        value = hidden.get("value")
        if name:
            payload[name] = value or ""

    today = date.today()
    date_from = today - timedelta(days=30)

    if guessed_dates.get("date_from"):
        payload[guessed_dates["date_from"]] = date_from.isoformat()
    if guessed_dates.get("date_to"):
        payload[guessed_dates["date_to"]] = today.isoformat()

    return payload


def attempt_search(
    method: str,
    action_url: str,
    payload: dict[str, str],
) -> SearchAttemptResult:
    """Attempt first search request using detected method and payload."""
    req_method = method.lower().strip() or "get"
    try:
        if req_method == "post":
            response = requests.post(
                action_url,
                data=payload,
                timeout=30,
                headers=REQUEST_HEADERS,
            )
        else:
            response = requests.get(
                action_url,
                params=payload,
                timeout=30,
                headers=REQUEST_HEADERS,
            )
        html = response.text
        SEARCH_ATTEMPT_HTML_PATH.write_text(html, encoding=response.encoding or "utf-8")
        return SearchAttemptResult(
            attempted=True,
            status_code=response.status_code,
            final_url=response.url,
            response_length=len(html),
        )
    except requests.RequestException as exc:
        return SearchAttemptResult(
            attempted=True,
            status_code=None,
            final_url=None,
            response_length=0,
            error=str(exc),
        )
    except OSError as exc:
        return SearchAttemptResult(
            attempted=True,
            status_code=None,
            final_url=None,
            response_length=0,
            error=f"Failed writing search attempt HTML: {exc}",
        )


def write_report(
    html_source: str,
    selected_index: int,
    action: str,
    method: str,
    total_fields: int,
    guessed_dates: dict[str, str | None],
    payload: dict[str, str],
    result: SearchAttemptResult,
) -> None:
    """Persist plain text report for Day 3 acceptance evidence."""
    lines = [
        "Court judgment search form probe report",
        f"html_source: {html_source}",
        f"selected_form_index: {selected_index}",
        f"detected_form_action: {action}",
        f"detected_form_method: {method}",
        f"total_fields_found: {total_fields}",
        (
            "guessed_date_fields: "
            f"from={guessed_dates.get('date_from')}, to={guessed_dates.get('date_to')}"
        ),
        f"search_request_attempted: {result.attempted}",
        f"response_status_code: {result.status_code}",
        f"final_url: {result.final_url}",
        f"response_length: {result.response_length}",
        f"payload_keys: {sorted(payload.keys())}",
    ]
    if result.error:
        lines.append(f"error: {result.error}")

    SEARCH_ATTEMPT_REPORT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_probe() -> int:
    """Run Day 3 form reverse-engineering + first search attempt."""
    html, html_source = ensure_html_source()
    if not html:
        return 1

    soup = BeautifulSoup(html, "html.parser")
    forms = soup.find_all("form")
    if not forms:
        print("No forms found on page.")
        return 2

    selected_idx, selected_form = pick_target_form(forms)
    if selected_form is None or selected_idx is None:
        print("Failed to select target form.")
        return 3

    all_form_summaries: list[dict[str, Any]] = [extract_fields(form) for form in forms]
    selected_summary = all_form_summaries[selected_idx]

    try:
        FORM_FIELDS_JSON_PATH.write_text(
            json.dumps(
                {
                    "source_url": TARGET_URL,
                    "html_source": html_source,
                    "forms_found": len(forms),
                    "selected_form_index": selected_idx,
                    "forms": all_form_summaries,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    except OSError as exc:
        print(f"Failed to write form fields json: {exc}")
        return 4

    guessed_dates = guess_date_fields(soup, selected_form, selected_summary)
    payload = build_min_payload(selected_summary, guessed_dates)

    detected_action = selected_summary.get("action") or ""
    action_url = urljoin(TARGET_URL, detected_action) if detected_action else TARGET_URL
    detected_method = (selected_summary.get("method") or "get").lower()

    total_fields = (
        len(selected_summary["inputs"])
        + len(selected_summary["selects"])
        + len(selected_summary["textareas"])
    )

    result = attempt_search(detected_method, action_url, payload)

    try:
        write_report(
            html_source=html_source,
            selected_index=selected_idx,
            action=action_url,
            method=detected_method,
            total_fields=total_fields,
            guessed_dates=guessed_dates,
            payload=payload,
            result=result,
        )
    except OSError as exc:
        print(f"Failed to write report: {exc}")
        return 5

    # Required terminal outputs for acceptance.
    print(f"detected form action: {action_url}")
    print(f"detected form method: {detected_method}")
    print(f"total fields found: {total_fields}")
    print(
        "guessed date fields: "
        f"from={guessed_dates.get('date_from')}, to={guessed_dates.get('date_to')}"
    )
    print(f"whether search request was attempted: {result.attempted}")
    print(f"response status code: {result.status_code}")
    print(f"final URL: {result.final_url}")
    print(f"response length: {result.response_length}")
    if result.error:
        print(f"error: {result.error}")

    print(f"saved_form_fields_json: {FORM_FIELDS_JSON_PATH}")
    print(f"saved_search_attempt_html: {SEARCH_ATTEMPT_HTML_PATH}")
    print(f"saved_search_attempt_report: {SEARCH_ATTEMPT_REPORT_PATH}")

    return 0


def main() -> None:
    raise SystemExit(run_probe())


if __name__ == "__main__":
    main()
