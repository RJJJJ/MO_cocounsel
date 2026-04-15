# Day 14 Acceptance

## Today objective

Fix pagination so it is **stateful** and starts from a **real submitted search-result state** (not from directly opening `researchjudgments?court=...&page=...` as independent entry pages).

## Deliverables

1. `crawler/parsers/court_playwright_result_pagination.py`
   - Uses Playwright to open search page, select court, and perform real submit.
   - Confirms page 1 is a true result page before paginating.
   - Paginates to page 2/page 3 using state-compatible URL derived from submitted result URL.
   - Applies valid/invalid page guard (including search-form-like detection).
   - Extracts required fields + `page_number`.
   - Aggregates and dedupes by `(court, case_number, decision_date, pdf_url or text_url_or_action)`.
   - Writes JSON + report outputs.

2. `crawler/parsers/court_playwright_result_pagination_spec.md`
   - Explains why direct URL-only pagination was insufficient.
   - Documents stateful navigation strategy and validity guards.
   - Defines dedupe and success criteria.

3. `data/parsed/court_probe/playwright_result_cards_paginated.json`
   - Aggregated, deduped cards from valid result pages only.

4. `data/parsed/court_probe/playwright_pagination_report.txt`
   - Run summary, page validity statuses, and success indicator.

## Acceptance checklist

- [ ] Real search is submitted before pagination starts.
- [ ] Court selection is applied to `tsi` / 中級法院 (or chosen `--court`).
- [ ] Page 1 true result state is validated.
- [ ] Pagination attempts pages 2/3 from submitted-state-compatible URL.
- [ ] Direct independent entry URL strategy is not used as primary flow.
- [ ] Invalid search-form-like pages are detected and explicitly reported.
- [ ] Invalid pages are not counted as successful parsed pages.
- [ ] Each kept record contains all required fields:
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
- [ ] Dedupe key follows required identity tuple.
- [ ] Outputs are written to required JSON/report paths.
- [ ] Terminal output includes:
  - `page 1 real result page reached: yes/no`
  - pages attempted
  - valid result pages parsed
  - invalid search-form-like pages detected
  - total cards before dedupe
  - total cards after dedupe
  - total resolved sentence URLs
  - whether stateful pagination appears successful
- [ ] No detail extraction and no batch fulltext extraction in this task.

## Evidence developer must provide

- Run command (example):
  - `python crawler/parsers/court_playwright_result_pagination.py --court tsi --pages 3`
- Terminal output excerpt containing required metrics and success flag.
- Generated artifacts:
  - `data/parsed/court_probe/playwright_result_cards_paginated.json`
  - `data/parsed/court_probe/playwright_pagination_report.txt`
- 3–5 sample records proving:
  - records came from valid result pages,
  - `page_number` is present,
  - dedupe applied across pages.
