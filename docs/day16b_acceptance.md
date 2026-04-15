# Day 16B acceptance

## Today objective
Fix paginated result-card **header token parsing** only, while keeping Day 14/15 pagination behavior and text/fulltext link preservation unchanged.

## Deliverables
- `crawler/parsers/court_playwright_result_header_fix.py`
- `crawler/parsers/court_playwright_result_header_fix_spec.md`
- `data/parsed/court_probe/playwright_result_cards_paginated_header_fixed.json`
- `data/parsed/court_probe/playwright_result_header_fix_report.txt`

## Acceptance checklist
- [ ] Uses Playwright and stateful search submission flow.
- [ ] Reuses paginated parsing for page 1/2/3.
- [ ] Preserves `pdf_url` and `text_url_or_action` extraction behavior from Day 15.
- [ ] Header parsing is strict-order and header-block based:
  - [ ] `decision_date`
  - [ ] `case_number`
  - [ ] `case_type`
- [ ] Table header labels are stripped before token parsing:
  - [ ] `判決/批示日期`
  - [ ] `案件編號`
  - [ ] `類別`
  - [ ] `裁判書/批示全文`
- [ ] Output records keep required fields:
  - [ ] `court`
  - [ ] `decision_date`
  - [ ] `case_number`
  - [ ] `case_type`
  - [ ] `pdf_url`
  - [ ] `text_url_or_action`
  - [ ] `subject`
  - [ ] `summary`
  - [ ] `decision_result`
  - [ ] `reporting_judge`
  - [ ] `assistant_judges`
  - [ ] `raw_card_text`
  - [ ] `page_number`
  - [ ] `text_link_language`
- [ ] Terminal output includes:
  - [ ] pages parsed
  - [ ] total cards after dedupe
  - [ ] valid case_number count
  - [ ] valid case_type count
  - [ ] records suspected of multi-card contamination
  - [ ] whether header fix appears successful
- [ ] No DB writes.
- [ ] No detail extraction.
- [ ] No batch全文抽取.

## Evidence developer must provide
- Command(s) used to run Day 16B parser (including page count).
- Terminal summary metrics listed above.
- Paths to generated JSON and report.
- A short statement confirming Day 14/15 behavior remained intact and only header parsing logic was changed.
