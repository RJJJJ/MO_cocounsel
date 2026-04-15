# Day 3 Acceptance - Form Reverse Engineering + First Search Attempt

## today objective
- Reverse engineer the Macau Courts judgment search form from the existing Day 2 HTML probe artifact.
- Determine form submission method/action and field structure.
- Attempt one minimal search request for the most recent 30 days and persist evidence artifacts.

## deliverables
- Probe script:
  - `crawler/source_probes/court_judgment_form_probe.py`
- Parser/result spec:
  - `crawler/parsers/court_judgment_result_spec.md`
- Probe-generated artifacts (from running the script):
  - `data/raw/court_probe/form_fields.json`
  - `data/raw/court_probe/search_attempt_last_30_days.html`
  - `data/raw/court_probe/search_attempt_report.txt`

## acceptance checklist
- [ ] Script uses `requests` + `BeautifulSoup` only (no Playwright).
- [ ] Script prefers local HTML `data/raw/court_probe/researchjudgments.html` when present.
- [ ] Script auto-refetches source page when local HTML is missing.
- [ ] Script detects at least one `<form>` and identifies target form for search.
- [ ] Script extracts and saves:
  - form action
  - form method
  - all input fields
  - all select fields
  - all textarea fields
  - all hidden fields
- [ ] Form structure saved to `data/raw/court_probe/form_fields.json`.
- [ ] Script attempts to infer judgment date-from/date-to field names.
- [ ] Script builds minimal last-30-days payload and attempts search request.
- [ ] Request method follows detected form method (`GET`/`POST`).
- [ ] Search response HTML saved to `data/raw/court_probe/search_attempt_last_30_days.html`.
- [ ] Text report saved to `data/raw/court_probe/search_attempt_report.txt`.
- [ ] Terminal output includes:
  - detected form action
  - detected form method
  - total fields found
  - guessed date fields
  - whether search request was attempted
  - response status code
  - final URL
  - response length
- [ ] No full ingestion pipeline, DB schema, or README changes are introduced.

## evidence developer must provide
- Exact command used to execute Day 3 probe script.
- Terminal output snippet with all required diagnostics.
- Artifact paths + file sizes for the three Day 3 outputs.
- Brief conclusion:
  - whether first search attempt reached a plausible result page,
  - and whether to stay with `requests` or escalate to Playwright next.
