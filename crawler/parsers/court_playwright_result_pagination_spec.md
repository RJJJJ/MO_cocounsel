# Day 14 Spec: Deterministic URL Pagination for Macau Courts Result Cards

## Why deterministic URL pagination is preferred now

Previous phases validated that result cards can be reliably extracted from Playwright-rendered pages. The main uncertainty was pagination traversal. After confirming stable query parameters (`court`, `page`), direct URL navigation is now preferred because it is:

- **Deterministic**: page 1, 2, 3 can be addressed directly without relying on fragile UI button state.
- **Lower-maintenance**: avoids selector drift and click/timing issues from pagination controls.
- **Easier to recover**: a single page failure can be logged and skipped without breaking full traversal.
- **Reproducible**: inputs are explicit (`court=tsi&page=2`) and suitable for reruns.

## Known court parameter mapping

- `tui` = 終審法院
- `tsi` = 中級法院
- `tjb` = 初級法院
- `ta`  = 行政法院
- `all` = 所有

## Known page parameter rule

Base path:

- `https://www.court.gov.mo/zh/subpage/researchjudgments?court=<court_code>`

Paginated pages:

- `...&page=2`
- `...&page=3`
- `...&page=<n>`

Implementation convention in this phase:

- Page 1 uses URL without explicit `page=1`.
- Pages >=2 include explicit `page=<n>`.

## Page loading strategy

For each target page number:

1. Build deterministic URL from known `court` and `page` query params.
2. `page.goto(url, wait_until="domcontentloaded")`.
3. Wait for stability (multi-round card-count stabilization).
4. Reuse validated DOM card extraction heuristic.
5. Parse normalized card fields and attach `page_number`.
6. If a page fails, record error and continue with remaining pages.

## Deduplication strategy

Aggregate all pages first, then deduplicate by strong identity:

- Primary identity tuple:
  - `(court, case_number, decision_date, pdf_url or text_url_or_action)`
- Fallback when key fields are missing:
  - `(court, raw_card_text)`

This minimizes duplicate carryover when the same judgment appears across pages or partial snapshots.

## Success criteria

A run is considered successful when:

- deterministic URLs are attempted for at least pages 1–3,
- at least two pages parse successfully,
- non-empty card output is produced,
- output files are written:
  - `data/parsed/court_probe/playwright_result_cards_paginated.json`
  - `data/parsed/court_probe/playwright_pagination_report.txt`
- terminal/report include:
  - court code used
  - pages attempted
  - pages successfully parsed
  - total cards before/after dedupe
  - total resolved sentence URLs
  - pagination success flag

## Recommended next step

Choose one of:

1. **Batch text-detail extraction from paginated cards**
   - Input from deduplicated paginated result-card pool.
   - Prioritize resolved `text_url_or_action` sentence URLs.

2. **Build raw corpus storage layout**
   - Separate index metadata (result cards) from full text corpus files.
   - Keep immutable raw snapshots + normalized structured layers for reproducibility.
