# Day 11 Acceptance

## Today objective

Refine Playwright result-card extraction and resolve TXT/fulltext entry handling so we can extract real text-detail content for downstream RAG ingestion.

## Deliverables

1. `crawler/parsers/court_playwright_text_detail_extractor.py`
   - Day 10 flow 기반單次查詢（no pagination）
   - refined card field parsing
   - TXT/fulltext entry resolution (href + onclick + popup/modal heuristics)
   - 1–3 text-detail sample extraction by real click
2. `crawler/parsers/court_playwright_text_detail_spec.md`
3. Output artifacts:
   - `data/parsed/court_probe/playwright_result_cards_refined.json`
   - `data/parsed/court_probe/playwright_text_details_sample.json`
   - `data/parsed/court_probe/playwright_text_details_report.txt`

## Acceptance checklist

- [ ] `case_number` correctly parsed as docket-style value (e.g., `253/2026`) instead of date prefix.
- [ ] `case_type` parsed from dedicated type field, not `/2026` artifact.
- [ ] `decision_result` extraction improved with label-aware parsing.
- [ ] `reporting_judge` extraction improved with label-aware parsing.
- [ ] TXT/fulltext entry resolution does not rely only on plain href text.
- [ ] Mechanism inspects clickable elements and related action metadata (`onclick`, JS trigger, popup/modal possibility).
- [ ] 1–3 real sample text-details extracted via TXT/fulltext entry clicking.
- [ ] Output JSON/report files are generated in `data/parsed/court_probe/`.
- [ ] Terminal output includes required counters and success boolean.
- [ ] No DB integration, no pagination, no full batch download.

## Evidence developer must provide

- Command used to run Day 11 extractor.
- Terminal counters:
  - total cards parsed
  - corrected case_number hit count
  - corrected case_type hit count
  - text entry resolved count
  - sample text details extracted count
  - whether txt/fulltext extraction appears successful
- Snippet (or JSON preview) proving:
  - refined `case_number` / `case_type`
  - non-null `text_url_or_action`
  - extracted `full_text` from TXT/fulltext sample.
