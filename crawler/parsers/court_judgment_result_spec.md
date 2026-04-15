# Court Judgment Result Spec (Day 3 Form Reverse Engineering)

## Source name
- Macau Courts Judgment Search (澳門法院裁判搜索)

## Search request method
- To be detected from HTML form parsing by `court_judgment_form_probe.py`.
- Expected output is recorded in:
  - `data/raw/court_probe/form_fields.json`
  - `data/raw/court_probe/search_attempt_report.txt`

## Search request action
- To be detected from target `<form action="...">`.
- Final absolute action URL is resolved with `urljoin(base_url, form_action)`.

## Observed form fields
- Full observed field inventory is persisted to `data/raw/court_probe/form_fields.json`, including:
  - all `input` fields
  - all `select` fields
  - all `textarea` fields
  - hidden fields (`input[type=hidden]`)

## Guessed date filter fields
- Probe attempts to infer "judgment date from/to" field names via:
  - field `name` / `id`
  - related `<label for="...">` text
  - placeholders
  - lexical markers: `date`, `日期`, `宣判`, `from/start/begin`, `to/end/until`, `起/由/至/迄`
- Guesses are recorded in terminal output and report.

## Test query window
- Last 30 days, computed as:
  - `date_from = today - 30 days`
  - `date_to = today`
- Payload includes:
  - hidden defaults
  - guessed date-from/date-to fields (if identified)

## Whether result page was reached
- First result-page fetch attempt is considered reached if:
  - HTTP request is sent successfully, and
  - response HTML is saved to `data/raw/court_probe/search_attempt_last_30_days.html`
- Status, final URL, and response length are documented in report.

## Expected result item fields
- To be confirmed by parsing the fetched result HTML. Initial expected fields:
  - judgment title / summary
  - court name
  - case number
  - judgment date
  - link to judgment detail or document
  - pagination metadata (page number, total count)

## Unknowns / to be confirmed
- Whether the search endpoint enforces additional anti-CSRF or dynamic tokens.
- Whether date fields require specific format (e.g., `YYYY-MM-DD` vs locale format).
- Whether required filters (court/type/etc.) must be supplied beyond date range.
- Whether search results are server-rendered or JavaScript-rendered.
- Whether redirects or localization state affect repeatable retrieval.

## Decision
- **Current decision:** stay with `requests` for Day 3 probe execution.
- **Escalate to Playwright only if** result listing cannot be reproduced from static HTTP requests (e.g., JS-only rendering or dynamic runtime token generation).
