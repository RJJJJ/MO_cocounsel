"""Day 5 probe: refine POST payload matrix for Macau Courts judgment search.

Scope:
- requests + BeautifulSoup only
- read existing form field information (Day 3 artifact)
- test multiple payload variants against the same endpoint
- persist per-variant HTML + summary artifacts

Out of scope:
- Playwright/browser automation
- database writes
- production crawler pipeline
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

FORM_FIELDS_PATH = Path("data/raw/court_probe/form_fields.json")
OUTPUT_DIR = Path("data/raw/court_probe/payload_matrix")
AGGREGATE_REPORT_PATH = OUTPUT_DIR / "payload_matrix_report.json"
TARGET_FALLBACK_URL = "https://www.court.gov.mo/zh/subpage/researchjudgments"

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

SEARCH_FORM_MARKERS: tuple[str, ...] = (
    "裁判書搜尋",
    "宣判日期",
    "案件編號",
    "法院",
    "種類",
    "查詢",
)

CANDIDATE_RESULT_MARKERS: tuple[str, ...] = (
    "裁判書",
    "案件",
    "編號",
    "判決",
    "上訴",
    "下載",
    "詳情",
    "結果",
)

CASE_NUMBER_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\b\d{1,6}/\d{2,4}\b"),
    re.compile(r"\b[A-Z]{1,4}-?\d{1,6}/\d{2,4}\b", re.IGNORECASE),
)


@dataclass
class VariantResult:
    payload_name: str
    payload_keys: list[str]
    response_status: int | None
    final_url: str | None
    response_length: int
    looks_like_search_form: bool
    appears_to_contain_candidate_markers: bool
    search_form_marker_hits: int
    candidate_marker_hits: int
    case_number_hits: int
    html_output_path: str
    summary_output_path: str
    error: str | None = None

    @property
    def score(self) -> int:
        """Simple score used for ranking candidate payload variants."""
        score = self.candidate_marker_hits + (self.case_number_hits * 2)
        if self.appears_to_contain_candidate_markers:
            score += 5
        score -= self.search_form_marker_hits
        if not self.looks_like_search_form:
            score += 3
        if self.response_status == 200:
            score += 1
        return score


def load_form_fields() -> dict[str, Any] | None:
    if not FORM_FIELDS_PATH.exists():
        print(f"Missing required form field artifact: {FORM_FIELDS_PATH}")
        print("Please run Day 3 form probe first to generate form_fields.json.")
        return None

    try:
        return json.loads(FORM_FIELDS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Failed to read/parse form fields artifact: {exc}")
        return None


def choose_target_form(data: dict[str, Any]) -> dict[str, Any] | None:
    forms = data.get("forms")
    selected_index = data.get("selected_form_index")

    if not isinstance(forms, list) or not forms:
        return None
    if isinstance(selected_index, int) and 0 <= selected_index < len(forms):
        item = forms[selected_index]
        return item if isinstance(item, dict) else None

    first = forms[0]
    return first if isinstance(first, dict) else None


def pick_date_fields(form: dict[str, Any]) -> tuple[str | None, str | None]:
    candidates: list[str] = []
    for entry in form.get("inputs", []):
        name = entry.get("name") if isinstance(entry, dict) else None
        if isinstance(name, str) and name.strip():
            candidates.append(name)

    from_field: str | None = None
    to_field: str | None = None
    for name in candidates:
        low = name.lower()
        if from_field is None and any(token in low for token in ("from", "start", "begin", "min")):
            from_field = name
        if to_field is None and any(token in low for token in ("to", "end", "until", "max")):
            to_field = name

    date_like = [
        n
        for n in candidates
        if any(token in n.lower() for token in ("date", "day", "判", "宣判", "日期"))
    ]
    if from_field is None and date_like:
        from_field = date_like[0]
    if to_field is None and len(date_like) > 1:
        to_field = date_like[1]

    return from_field, to_field


def pick_field_name(form: dict[str, Any], tokens: tuple[str, ...]) -> str | None:
    for entry in form.get("inputs", []):
        if not isinstance(entry, dict):
            continue
        raw = " ".join(
            [
                str(entry.get("name") or ""),
                str(entry.get("id") or ""),
                str(entry.get("placeholder") or ""),
            ]
        ).lower()
        if any(token in raw for token in tokens):
            name = entry.get("name")
            if isinstance(name, str) and name.strip():
                return name

    for entry in form.get("textareas", []):
        if not isinstance(entry, dict):
            continue
        raw = " ".join([str(entry.get("name") or ""), str(entry.get("id") or "")]).lower()
        if any(token in raw for token in tokens):
            name = entry.get("name")
            if isinstance(name, str) and name.strip():
                return name

    return None


def pick_select_field_and_value(form: dict[str, Any], tokens: tuple[str, ...]) -> tuple[str | None, str | None]:
    for sel in form.get("selects", []):
        if not isinstance(sel, dict):
            continue

        raw = " ".join([str(sel.get("name") or ""), str(sel.get("id") or "")]).lower()
        if not any(token in raw for token in tokens):
            continue

        field_name = sel.get("name")
        if not isinstance(field_name, str) or not field_name.strip():
            continue

        options = sel.get("options") if isinstance(sel.get("options"), list) else []
        for option in options:
            if not isinstance(option, dict):
                continue
            value = option.get("value")
            text = str(option.get("text") or "").strip()
            if value is None:
                continue
            value_s = str(value)
            if value_s.strip() and text not in {"全部", "全部法院", "全部種類", "All"}:
                return field_name, value_s

        if options:
            first = options[0]
            if isinstance(first, dict) and first.get("value") is not None:
                return field_name, str(first.get("value"))

    return None, None


def build_base_payload(form: dict[str, Any]) -> dict[str, str]:
    payload: dict[str, str] = {}
    for hidden in form.get("hidden_fields", []):
        if not isinstance(hidden, dict):
            continue
        name = hidden.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        payload[name] = str(hidden.get("value") or "")
    return payload


def count_hits(text: str, markers: tuple[str, ...]) -> int:
    return sum(1 for marker in markers if marker in text)


def detect_search_form(soup: BeautifulSoup, text: str) -> tuple[bool, int]:
    marker_hits = count_hits(text, SEARCH_FORM_MARKERS)
    has_form = soup.find("form") is not None
    return has_form and marker_hits >= 3, marker_hits


def detect_candidate_markers(text: str) -> tuple[bool, int, int]:
    marker_hits = count_hits(text, CANDIDATE_RESULT_MARKERS)
    case_hits = sum(len(pattern.findall(text)) for pattern in CASE_NUMBER_PATTERNS)
    appears = marker_hits >= 3 or case_hits >= 2
    return appears, marker_hits, case_hits


def make_date_strings(base_day: date, fmt: str) -> tuple[str, str]:
    start_day = base_day - timedelta(days=30)
    if fmt == "YYYY/MM/DD":
        return start_day.strftime("%Y/%m/%d"), base_day.strftime("%Y/%m/%d")
    return start_day.strftime("%Y-%m-%d"), base_day.strftime("%Y-%m-%d")


def persist_variant_artifacts(name: str, html: str, summary: dict[str, Any]) -> tuple[Path, Path]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    html_path = OUTPUT_DIR / f"{name}.html"
    summary_path = OUTPUT_DIR / f"{name}_summary.json"
    html_path.write_text(html, encoding="utf-8")
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return html_path, summary_path


def execute_variant(endpoint: str, payload_name: str, payload: dict[str, str]) -> VariantResult:
    html = ""
    status_code: int | None = None
    final_url: str | None = None
    error: str | None = None

    try:
        response = requests.post(endpoint, data=payload, headers=REQUEST_HEADERS, timeout=30)
        status_code = response.status_code
        final_url = response.url
        html = response.text
    except requests.RequestException as exc:
        error = str(exc)

    soup = BeautifulSoup(html or "", "html.parser")
    text = soup.get_text(" ", strip=True)

    looks_like_form, form_hits = detect_search_form(soup, text)
    appears_candidate, candidate_hits, case_hits = detect_candidate_markers(text)

    summary_data: dict[str, Any] = {
        "payload_name": payload_name,
        "payload": payload,
        "payload_keys": sorted(payload.keys()),
        "response_status": status_code,
        "final_url": final_url,
        "response_length": len(html),
        "looks_like_search_form": looks_like_form,
        "appears_to_contain_candidate_markers": appears_candidate,
        "search_form_marker_hits": form_hits,
        "candidate_marker_hits": candidate_hits,
        "case_number_hits": case_hits,
        "error": error,
    }

    html_path, summary_path = persist_variant_artifacts(payload_name, html, summary_data)

    return VariantResult(
        payload_name=payload_name,
        payload_keys=sorted(payload.keys()),
        response_status=status_code,
        final_url=final_url,
        response_length=len(html),
        looks_like_search_form=looks_like_form,
        appears_to_contain_candidate_markers=appears_candidate,
        search_form_marker_hits=form_hits,
        candidate_marker_hits=candidate_hits,
        case_number_hits=case_hits,
        html_output_path=str(html_path),
        summary_output_path=str(summary_path),
        error=error,
    )


def best_variant(results: list[VariantResult]) -> VariantResult | None:
    if not results:
        return None
    return sorted(
        results,
        key=lambda r: (
            r.score,
            not r.looks_like_search_form,
            r.appears_to_contain_candidate_markers,
            r.response_length,
        ),
        reverse=True,
    )[0]


def run_probe() -> int:
    data = load_form_fields()
    if data is None:
        return 1

    form = choose_target_form(data)
    if form is None:
        print("No valid target form found in form_fields.json")
        return 2

    endpoint = urljoin(
        str(data.get("source_url") or TARGET_FALLBACK_URL),
        str(form.get("action") or ""),
    )

    date_from_field, date_to_field = pick_date_fields(form)
    if not date_from_field or not date_to_field:
        print("Unable to identify date range fields from form metadata.")
        return 3

    court_field, court_value = pick_select_field_and_value(form, ("court", "法院"))
    proc_field, proc_value = pick_select_field_and_value(form, ("proc", "type", "種類"))
    keyword_field = pick_field_name(form, ("reccontent", "content", "keyword", "全文"))

    base_payload = build_base_payload(form)

    if not base_payload:
        print("Warning: no hidden/token fields found; proceeding with explicit fields only.")

    date_formats = ["YYYY-MM-DD", "YYYY/MM/DD"]
    variants: list[tuple[str, dict[str, str]]] = []

    for fmt in date_formats:
        start_str, end_str = make_date_strings(date.today(), fmt)

        payload_a = {
            **base_payload,
            date_from_field: start_str,
            date_to_field: end_str,
        }
        variants.append((f"A_token_date_only_{fmt.replace('/', '-')}", payload_a))

        if court_field and court_value is not None:
            payload_b = {**payload_a, court_field: court_value}
            variants.append((f"B_plus_court_{fmt.replace('/', '-')}", payload_b))

            if proc_field and proc_value is not None:
                payload_c = {**payload_b, proc_field: proc_value}
                variants.append((f"C_plus_court_proctype_{fmt.replace('/', '-')}", payload_c))

            if keyword_field:
                payload_d = {**payload_b, keyword_field: "合同"}
                variants.append((f"D_plus_court_keyword_{fmt.replace('/', '-')}", payload_d))

    if len(variants) < 4:
        print("Insufficient payload variants generated (<4).")
        return 4

    results: list[VariantResult] = []
    for payload_name, payload in variants:
        result = execute_variant(endpoint, payload_name, payload)
        results.append(result)

    best = best_variant(results)
    reduced_form_markers = any(not item.looks_like_search_form for item in results)

    recommendation = (
        "stay with requests"
        if best
        and best.appears_to_contain_candidate_markers
        and not best.looks_like_search_form
        else "escalate"
    )

    aggregate: dict[str, Any] = {
        "endpoint_under_test": endpoint,
        "total_payload_variants_tested": len(results),
        "tested_date_formats": date_formats,
        "best_candidate_payload": best.payload_name if best else None,
        "whether_any_variant_reduced_form_page_markers": reduced_form_markers,
        "recommendation": recommendation,
        "variants": [
            {
                "payload_name": item.payload_name,
                "payload_keys": item.payload_keys,
                "response_status": item.response_status,
                "final_url": item.final_url,
                "response_length": item.response_length,
                "looks_like_search_form": item.looks_like_search_form,
                "appears_to_contain_candidate_case_or_result_markers": (
                    item.appears_to_contain_candidate_markers
                ),
                "search_form_marker_hits": item.search_form_marker_hits,
                "candidate_marker_hits": item.candidate_marker_hits,
                "case_number_hits": item.case_number_hits,
                "score": item.score,
                "html_output_path": item.html_output_path,
                "summary_output_path": item.summary_output_path,
                "error": item.error,
            }
            for item in results
        ],
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    AGGREGATE_REPORT_PATH.write_text(
        json.dumps(aggregate, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"endpoint under test: {endpoint}")
    print(f"total payload variants tested: {len(results)}")
    print(f"best candidate payload: {best.payload_name if best else 'N/A'}")
    print(f"whether any variant reduced form-page markers: {reduced_form_markers}")
    print(f"recommendation: {recommendation}")
    print(f"saved aggregate report: {AGGREGATE_REPORT_PATH}")

    return 0


def main() -> None:
    raise SystemExit(run_probe())


if __name__ == "__main__":
    main()
