# Day 17 Acceptance

## Today Objective

Implement a strict selector-based parser for Macau Courts result cards using the confirmed DOM
structure, covering pages 1, 2, and 3 in a stateful Playwright search flow.

## Deliverables

1. `crawler/parsers/court_selector_driven_result_parser.py`
   - Uses Playwright
   - Stateful flow: open search page -> select 中級法院 -> submit -> parse page 1 -> parse pages 2/3
   - Strict selector parsing for result cards (`div#zh-language-case.case_list > li`)
   - Excludes separator `li.seperate`
   - Extracts:
     - `decision_date` from `span.date`
     - `case_number` from `span.num`
     - `case_type` from `span.type`
     - document links from `span.download a`
   - Href-first document classification
   - Dedupe key: `(court, case_number, decision_date, text_url_or_action or pdf_url)`
   - Writes:
     - `data/parsed/court_probe/playwright_result_cards_selector_driven.json`
     - `data/parsed/court_probe/playwright_result_cards_selector_driven_report.txt`

2. `crawler/parsers/court_selector_driven_result_parser_spec.md`
   - Records confirmed DOM hierarchy
   - Explains authoritative card boundary (`li`)
   - Documents exclusion of `.seperate`
   - Documents exact field selectors and href-based classification rules
   - Lists deferred fields and next-step recommendations

3. `docs/day17_acceptance.md`
   - Objective, deliverables, checklist, and required evidence

## Acceptance Checklist

- [ ] Parser is selector-driven (no generic repeated-block scoring main path)
- [ ] Parser does not fuzzy-parse header fields from raw card text
- [ ] Pages 1, 2, 3 are parsed under the same submitted search state
- [ ] `li.seperate` and trivial cards are excluded
- [ ] `span.date`, `span.num`, `span.type`, `span.download a` are used
- [ ] Href-first link classification is implemented
- [ ] zh/pt text links are preserved (`text_url_zh`, `text_url_pt`)
- [ ] `text_url_or_action` prefers zh then pt
- [ ] `pdf_url` prefers zh pdf then pt pdf
- [ ] Required output JSON and report files are generated
- [ ] Report includes required metrics and success assessment
- [ ] No README changes
- [ ] No batch fulltext extraction
- [ ] No Day16B backtracking changes

## Evidence Developer Must Provide

- Command(s) used to run parser.
- Terminal output showing:
  - pages parsed
  - total cards before dedupe
  - total cards after dedupe
  - cards with decision_date
  - cards with case_number
  - cards with case_type
  - cards with pdf_url
  - cards with text_url_or_action
  - zh text links count
  - pt text links count
  - selector-driven success boolean
- Snippet or summary of output JSON schema showing required fields are present.
- Git diff summary proving only Day 17 requested files were added/updated.
