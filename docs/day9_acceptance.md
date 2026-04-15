# Day 9 Acceptance: Deterministic Result-Card Parser

## Today objective

Implement a deterministic parser that extracts **true Macau Courts judgment result cards** from requests-replay post-submit HTML and outputs structured JSON for downstream use.

## Deliverables

- `crawler/parsers/court_result_card_parser.py`
  - BeautifulSoup-based card parser
  - reads `data/raw/court_probe/requests_replay_after_submit.html`
  - writes:
    - `data/parsed/court_probe/requests_result_cards.json`
    - `data/parsed/court_probe/requests_result_cards_report.txt`
  - deterministic card-container selection
  - required fields extraction
  - terminal summary metrics
- `crawler/parsers/court_result_card_spec.md`
  - rationale, structure confirmation, mapping, assumptions, goals, next steps
- `docs/day9_acceptance.md` (this file)

## Acceptance checklist

- [ ] Parser uses BeautifulSoup only (no Playwright).
- [ ] Parser is card-oriented (not generic mixed-block exploration).
- [ ] Parser reads replay HTML from `data/raw/court_probe/requests_replay_after_submit.html`.
- [ ] Parser outputs JSON to `data/parsed/court_probe/requests_result_cards.json`.
- [ ] Parser outputs report to `data/parsed/court_probe/requests_result_cards_report.txt`.
- [ ] Each card attempts to extract:
  - [ ] `court`
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
- [ ] Terminal output includes:
  - [ ] total cards detected
  - [ ] total cards parsed
  - [ ] hit count for major fields
  - [ ] whether output looks like true judgment cards
- [ ] No detail-page parsing.
- [ ] No pagination.
- [ ] No database writes.

## Evidence developer must provide

1. Command(s) used to run parser.
2. Terminal output showing required metrics.
3. First 1–3 JSON records from `requests_result_cards.json`.
4. Report excerpt from `requests_result_cards_report.txt` with field hit counts.
5. Brief statement confirming no detail-page parsing and no pagination were implemented.
