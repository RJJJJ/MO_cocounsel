# Day 12 Acceptance

## Today objective
Fix TXT/fulltext detail extraction by treating resolved sentence URLs as direct detail pages, extracting 1–3 non-empty text samples, and capturing language (`zh` / `pt`) from URL path.

## Deliverables
- `crawler/parsers/court_playwright_text_detail_fix.py`
- `crawler/parsers/court_playwright_text_detail_fix_spec.md`
- `data/parsed/court_probe/playwright_text_details_sample.json`
- `data/parsed/court_probe/playwright_text_details_fix_report.txt`
- `docs/day12_acceptance.md`

## Acceptance checklist
- [ ] Reads `data/parsed/court_probe/playwright_result_cards_refined.json`.
- [ ] Selects first 1–3 cards with `text_url_or_action` sentence URLs.
- [ ] Uses direct `page.goto(text_url_or_action)` as primary path.
- [ ] Uses popup/modal/overlay only as fallback after direct navigation failure.
- [ ] Extracts non-empty, substantive `full_text` (not metadata-only).
- [ ] Captures fields per sample:
  - [ ] `case_number`
  - [ ] `decision_date`
  - [ ] `title_or_issue`
  - [ ] `full_text`
  - [ ] `source_type` (`txt/fulltext`)
  - [ ] `extracted_from`
  - [ ] `language`
- [ ] Language rule works:
  - [ ] `/zh/` -> `zh`
  - [ ] `/pt/` -> `pt`
  - [ ] else -> `unknown`
- [ ] Terminal output includes:
  - [ ] sample cards attempted
  - [ ] successful text detail extractions
  - [ ] failed detail extractions
  - [ ] direct sentence pages opened count
  - [ ] language counts
  - [ ] whether text extraction now appears successful
- [ ] No pagination added.
- [ ] No batch extraction added.
- [ ] No DB integration added.

## Evidence developer must provide
- Command used to run Day 12 fix script.
- Console output excerpt showing counters and success status.
- `playwright_text_details_sample.json` snippet proving at least one non-empty `full_text`.
- `playwright_text_details_fix_report.txt` snippet showing final metrics.
