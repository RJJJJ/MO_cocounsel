# Day 16 Acceptance

## Today objective

Fix paginated result-card segmentation so each extracted JSON record corresponds to exactly one judgment card, while preserving Day 14/15 stateful pagination and document links.

## Deliverables

1. `crawler/parsers/court_playwright_result_card_boundary_fix.py`
   - Uses Playwright.
   - Reuses stateful pagination flow from submitted result-page state.
   - Parses pages 1/2/3.
   - Prioritizes stable repeated DOM container segmentation and atomic card selection.
   - Ensures one card container -> one JSON record.
   - Preserves required fields:
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
     - `text_link_language`
   - Writes clean paginated JSON and boundary-fix report outputs.

2. `crawler/parsers/court_playwright_result_card_boundary_fix_spec.md`
   - Explains Day 15 boundary regression and why link preservation alone was insufficient.
   - Defines DOM-first segmentation + field isolation strategy.
   - Defines contamination detection and success criteria.
   - Recommends next-step extraction work.

3. `data/parsed/court_probe/playwright_result_cards_paginated_clean.json`
   - Clean paginated cards for next-step text extraction.

4. `data/parsed/court_probe/playwright_result_card_boundary_fix_report.txt`
   - Boundary-fix metrics and page-attempt evidence.

## Acceptance checklist

- [ ] Stateful pagination flow is reused from submitted search result state.
- [ ] Pages 1/2/3 are attempted.
- [ ] Segmentation is DOM-container based (not only global regex on merged text).
- [ ] One output record corresponds to one card container.
- [ ] `case_number` quality is restored (normalized number/year style).
- [ ] `case_type` is not malformed residual like `/2026`.
- [ ] `subject`/`summary` are isolated to the same card.
- [ ] `pdf_url` and `text_url_or_action` are preserved.
- [ ] Output JSON/report paths are generated.
- [ ] Terminal output includes:
  - pages parsed
  - total cards before dedupe
  - total cards after dedupe
  - valid case_number count
  - valid case_type count
  - records suspected of multi-card contamination
  - whether card-boundary fix appears successful
- [ ] No detail-page extraction.
- [ ] No batch fulltext extraction.

## Evidence developer must provide

1. Run command (example):
   - `python crawler/parsers/court_playwright_result_card_boundary_fix.py --court tsi --pages 3`
2. Terminal output excerpt containing required Day 16 metrics.
3. Generated artifacts:
   - `data/parsed/court_probe/playwright_result_cards_paginated_clean.json`
   - `data/parsed/court_probe/playwright_result_card_boundary_fix_report.txt`
4. Sample records proving:
   - one-card-per-record segmentation,
   - valid `case_number`/`case_type` shape,
   - preserved `pdf_url`/`text_url_or_action`.
