# Day 8 Acceptance

## Today objective
Implement a **requests-result-list parser probe** that reads the Day 7 replay HTML artifact and extracts structured result list items for inspection.

## Deliverables
- `crawler/parsers/court_requests_result_list_parser.py`
- `crawler/parsers/court_requests_result_list_spec.md`
- Generated artifacts (from parser run):
  - `data/parsed/court_probe/requests_result_items.json`
  - `data/parsed/court_probe/requests_result_items_report.txt`

## Acceptance checklist
- [ ] Uses BeautifulSoup (no Playwright).
- [ ] Reads input from `data/raw/court_probe/requests_replay_after_submit.html`.
- [ ] Performs exploratory parsing across:
  - [ ] table rows
  - [ ] list items
  - [ ] repeated div/section/article blocks
  - [ ] links near case/date text
- [ ] Extracts fields as available:
  - [ ] `raw_text`
  - [ ] `title`
  - [ ] `case_number`
  - [ ] `judgment_date`
  - [ ] `court`
  - [ ] `detail_url`
  - [ ] `document_url`
- [ ] Writes JSON output to `data/parsed/court_probe/requests_result_items.json`.
- [ ] Writes parser report to `data/parsed/court_probe/requests_result_items_report.txt`.
- [ ] Terminal output includes at least:
  - [ ] total candidate blocks found
  - [ ] total result items extracted
  - [ ] structure guess (table/list/card/mixed)
  - [ ] number of items with case number
  - [ ] number of items with date
  - [ ] number of items with detail link
- [ ] Includes `main()` and basic error handling.
- [ ] Does not implement full crawler / DB integration.

## Evidence developer must provide
- Parser execution command and output log.
- Existence and content preview of:
  - `data/parsed/court_probe/requests_result_items.json`
  - `data/parsed/court_probe/requests_result_items_report.txt`
- Git diff showing only Day 8 parser-probe related files.
