# Day 18 Acceptance

## Today objective

Implement batch text-detail extraction from Day 17 selector-driven result cards, using a body-first strategy for Macau Courts sentence/TXT detail pages.

## Deliverables

1. `crawler/parsers/court_playwright_text_batch_from_selector_cards.py`
   - reads `data/parsed/court_probe/playwright_result_cards_selector_driven.json`
   - iterates cards with usable `text_url_or_action`
   - opens each detail page with Playwright
   - performs body-first extraction and print-block cleanup
   - parses authoritative detail metadata from normalized text
   - writes:
     - `data/parsed/court_probe/playwright_text_details_from_selector_cards.jsonl`
     - `data/parsed/court_probe/playwright_text_details_from_selector_cards_report.txt`

2. `crawler/parsers/court_playwright_text_batch_from_selector_cards_spec.md`
   - documents extraction rationale and rules

3. `docs/day18_acceptance.md`
   - objective, checklist, and evidence requirements

## Acceptance checklist

- [ ] Does not modify Day 17 parser.
- [ ] Does not touch database integration.
- [ ] Uses selector-driven cards as the only batch entry input.
- [ ] Uses body-first extraction for sentence/TXT pages (not complex selector-first dependency).
- [ ] Ignores/removes print block and print-link chrome.
- [ ] Normalizes whitespace/blank lines before parsing metadata.
- [ ] Parses `detail_case_number`, `detail_decision_date`, `detail_title_or_issue`, `language`, `full_text`.
- [ ] Retains source-layer fields for comparison/debugging.
- [ ] Writes required JSONL and report output files.
- [ ] Terminal output includes required run summary metrics.

## Evidence developer must provide

1. Command(s) run for verification (at minimum):
   - static syntax check (`python -m py_compile ...`)
   - one execution attempt of Day 18 script (with observed summary output)

2. Snippets of generated artifacts:
   - first 1–2 lines of JSONL output
   - key report lines showing attempted/succeeded/failed and language counts

3. Git evidence:
   - committed changes on current branch
   - PR title/body prepared via `make_pr`
