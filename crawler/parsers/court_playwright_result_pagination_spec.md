# Day 14 Spec: Stateful Pagination from Real Submitted Result State

## Why the previous direct URL pagination approach was insufficient

The prior Day 14 attempt treated URLs like `.../researchjudgments?court=tsi&page=2` as independent entry points. In practice, opening those URLs directly can render search-page chrome (or form-like shell) rather than true repeated judgment result cards. That means a URL can look paginated but still not represent a valid result dataset.

## Why pagination must start from a real submitted result-page state

Pagination must begin only after Playwright performs a real UI search submission:

1. Open the search page.
2. Select target court (`tsi` / 中級法院).
3. Click search/submit.
4. Wait for true page-1 result cards to stabilize.

Only after this state exists do we derive page 2/3 URLs from the submitted result URL. This keeps query/state parameters aligned with real server-side result context.

## Updated navigation strategy

1. `page.goto(search_page)`.
2. Programmatically set/select court in the real court selector.
3. Trigger actual submit click (`搜索/查詢/search/pesquisa` button or form submit fallback).
4. Wait for result-card stability on page 1.
5. Capture submitted result URL (`page.url`).
6. Parse page 1 cards.
7. Build page 2/3 URLs by mutating only `page` on the submitted URL.
8. For each next page:
   - `goto(state_compatible_paginated_url)`
   - wait for stabilization
   - run valid-page guard
   - parse cards only if valid
   - attach `page_number`

## Valid-page vs invalid-page detection criteria

A page is valid only if it contains strong result-card signals:

- multiple repeated card-like blocks (`repeated_count >= 3`, with at least 2 blocks),
- meaningful case-number hits,
- non-empty `pdf_url` or `text_url_or_action` on at least 2 blocks.

Invalid-page handling:

- If criteria fail and DOM resembles search-form shell (many form controls, search keywords, low case-card candidates), mark page invalid with `search_form_like_page_detected`.
- Invalid pages are explicitly reported and excluded from successful pagination output.

## Deduplication strategy

Aggregate all valid parsed cards, then dedupe by:

- `(court, case_number, decision_date, pdf_url or text_url_or_action)`

Fallback key when these are absent:

- `(court, raw_card_text)`

## Success criteria

A run is considered successful when:

- page 1 is reached via real submitted result state,
- pages 1..N are attempted from state-compatible URLs,
- at least two pages are valid result pages,
- output artifacts are generated:
  - `data/parsed/court_probe/playwright_result_cards_paginated.json`
  - `data/parsed/court_probe/playwright_pagination_report.txt`
- terminal/report contain:
  - `page 1 real result page reached: yes/no`
  - pages attempted
  - valid result pages parsed
  - invalid search-form-like pages detected
  - total cards before/after dedupe
  - total resolved sentence URLs
  - stateful pagination success flag

## Recommended next step

Choose one:

1. Batch text-detail extraction from deduped paginated cards.
2. Build raw corpus storage layout for index metadata + immutable raw text snapshots.

(Out of scope for this Day 14 stateful-pagination fix.)
