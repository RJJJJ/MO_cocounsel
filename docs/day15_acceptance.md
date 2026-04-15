# Day 15 Acceptance

## Today objective

Fix paginated result-card extraction so text/fulltext links are preserved correctly across pages 1/2/3 while keeping Day 14 stateful pagination behavior unchanged.

## Deliverables

1. `crawler/parsers/court_playwright_result_pagination_refine.py`
   - Uses Playwright.
   - Reuses stateful pagination flow from real submitted result state.
   - Parses pages 1/2/3.
   - Strengthens in-card document extraction across anchors/icons/buttons/spans.
   - Preserves:
     - `pdf_url`
     - `text_url_or_action` (including action descriptor fallback)
     - zh/pt sentence-link detection.
   - Keeps required card schema + `page_number`.
   - Dedupes by `(court, case_number, decision_date, pdf_url or text_url_or_action)`.
   - Writes refined JSON and report outputs.

2. `crawler/parsers/court_playwright_result_pagination_refine_spec.md`
   - Documents why Day 14 pagination is successful.
   - Explains text/fulltext preservation bottleneck.
   - Defines refined extraction strategy and zh/pt rules.
   - Defines success criteria and next-step options.

3. `data/parsed/court_probe/playwright_result_cards_paginated_refined.json`
   - Refined deduped paginated cards with preserved document entry links/actions.

4. `data/parsed/court_probe/playwright_pagination_refined_report.txt`
   - Metrics and success signal for paginated text-link preservation.

## Acceptance checklist

- [ ] Day 14 stateful pagination behavior is preserved.
- [ ] Pages 1/2/3 are attempted from submitted result-state-compatible URL.
- [ ] In-card extraction does not rely only on link label text.
- [ ] Extraction scans anchors/buttons/spans/icons and related attributes.
- [ ] Output schema includes required fields:
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
- [ ] Deduplication key follows required tuple identity.
- [ ] Refined outputs are written to required JSON/report paths.
- [ ] Terminal output contains:
  - pages parsed
  - total cards before dedupe
  - total cards after dedupe
  - cards with pdf_url
  - cards with text_url_or_action
  - cards with both
  - zh text links count
  - pt text links count
  - whether paginated text-link resolution appears successful
- [ ] No detail-page extraction.
- [ ] No batch fulltext extraction.

## Evidence developer must provide

1. Run command (example):
   - `python crawler/parsers/court_playwright_result_pagination_refine.py --court tsi --pages 3`
2. Terminal output excerpt with required Day 15 metrics.
3. Generated artifacts:
   - `data/parsed/court_probe/playwright_result_cards_paginated_refined.json`
   - `data/parsed/court_probe/playwright_pagination_refined_report.txt`
4. 3–5 sample records proving:
   - `page_number` present,
   - `pdf_url` and/or `text_url_or_action` preserved,
   - cross-page dedupe applied.
