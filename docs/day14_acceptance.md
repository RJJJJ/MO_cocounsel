# Day 14 Acceptance

## Today objective

Implement deterministic URL-based pagination for Macau Courts judgment result pages and aggregate deduplicated result cards across multiple pages without relying on UI pagination button discovery.

## Deliverables

1. `crawler/parsers/court_playwright_result_pagination.py`
   - Playwright-based deterministic pagination extractor.
   - Default: `court=tsi`, at least first 3 pages.
   - Aggregation + deduplication across paginated pages.
   - Output JSON and report.

2. `crawler/parsers/court_playwright_result_pagination_spec.md`
   - Documents rationale, parameter mapping, loading strategy, dedupe strategy, success criteria, and next-step recommendation.

3. `data/parsed/court_probe/playwright_result_cards_paginated.json`
   - Aggregated and deduplicated paginated result-card records.

4. `data/parsed/court_probe/playwright_pagination_report.txt`
   - Run summary, per-page status, counts, and pagination-success indicator.

## Acceptance checklist

- [ ] Uses Playwright navigation (`page.goto`) for paginated result pages.
- [ ] Uses known query parameter scheme (`court`, `page`) as primary path.
- [ ] Attempts page 1 + 2 + 3 (or more when stable/configured).
- [ ] Extracts cards per page and preserves `page_number`.
- [ ] Includes required fields per card:
  - `court`
  - `decision_date`
  - `case_number`
  - `case_type`
  - `pdf_url`
  - `text_url_or_action`
  - `subject`
  - `summary`
  - `decision_result`
  - `reporting_judge`
  - `assistant_judges`
  - `raw_card_text`
  - `page_number`
- [ ] Aggregates and deduplicates cards across pages.
- [ ] Dedupes using strong identity key with document-link preference.
- [ ] Records failed page attempts without aborting full run.
- [ ] Writes JSON output and text report to required locations.
- [ ] Terminal output includes requested pagination metrics.
- [ ] No detail-page extraction and no batch fulltext extraction in this task.

## Evidence developer must provide

- Command used to run Day 14 parser (example):
  - `python crawler/parsers/court_playwright_result_pagination.py --court tsi --pages 3`
- Terminal output excerpt including:
  - court code used
  - pages attempted / successfully parsed
  - total cards before/after dedupe
  - total resolved sentence URLs
  - pagination success flag
- Artifacts generated:
  - `data/parsed/court_probe/playwright_result_cards_paginated.json`
  - `data/parsed/court_probe/playwright_pagination_report.txt`
- Short sample (3–5 records) showing records include `page_number` and deduped structure.
