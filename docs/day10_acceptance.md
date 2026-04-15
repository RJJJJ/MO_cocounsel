# Day 10 Acceptance: Playwright Rendered-DOM Result-Card Extraction

## Today objective

Switch Day 10 implementation path from requests-replay HTML parsing to **Playwright rendered-DOM extraction** for Macau Courts judgment result cards.

## Deliverables

- `crawler/parsers/court_playwright_result_card_extractor.py`
  - Playwright-based result-card extractor
  - opens `https://www.court.gov.mo/zh/subpage/researchjudgments`
  - submits one search (prefer `中級法院`, fallback acceptable)
  - waits for rendered results stabilization
  - extracts repeated cards from browser DOM
  - writes:
    - `data/parsed/court_probe/playwright_result_cards.json`
    - `data/parsed/court_probe/playwright_result_cards_report.txt`
  - saves artifacts:
    - `data/raw/court_probe/playwright_result_page.html`
    - `data/raw/court_probe/playwright_result_page.png`
  - prints terminal metrics
- `crawler/parsers/court_playwright_result_card_spec.md`
  - rationale, observed structure, extraction strategy, mapping, risks, next steps
- `docs/day10_acceptance.md` (this file)

## Acceptance checklist

- [ ] Uses Playwright for Python.
- [ ] Does **not** depend on requests replay HTML.
- [ ] Extracts repeated result cards from rendered page DOM.
- [ ] Attempts to extract each card field:
  - [ ] `decision_date`
  - [ ] `case_number`
  - [ ] `case_type`
  - [ ] `pdf_url`
  - [ ] `text_url`
  - [ ] `subject`
  - [ ] `summary`
  - [ ] `decision_result`
  - [ ] `reporting_judge`
  - [ ] `assistant_judges`
  - [ ] `raw_card_text`
  - [ ] `court`
- [ ] Outputs JSON to `data/parsed/court_probe/playwright_result_cards.json`.
- [ ] Outputs report to `data/parsed/court_probe/playwright_result_cards_report.txt`.
- [ ] Saves rendered page artifacts (HTML + PNG).
- [ ] Terminal output includes:
  - [ ] total cards detected
  - [ ] total cards parsed
  - [ ] hit count for major fields
  - [ ] whether output looks like true judgment cards
- [ ] Has `main()` and basic error handling.
- [ ] No pagination.
- [ ] No detail-page parsing.
- [ ] No database writes.

## Evidence developer must provide

1. Command used to run the extractor.
2. Terminal output showing required metrics.
3. First 1–3 JSON records from `playwright_result_cards.json`.
4. Report excerpt from `playwright_result_cards_report.txt` with field hit counts.
5. Confirmation that no pagination and no detail-page parsing were implemented.
6. Paths to saved rendered artifacts (HTML + screenshot).
