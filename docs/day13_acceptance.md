# Day 13 acceptance

## Today objective

Expand validated TXT/fulltext detail extraction into a controlled batch extractor using resolved sentence URLs, and persist a local text corpus batch (no pagination, no database).

## Deliverables

1. `crawler/parsers/court_playwright_text_detail_batch_extractor.py`
2. `crawler/parsers/court_playwright_text_detail_batch_spec.md`
3. `docs/day13_acceptance.md`
4. Updated Day 12 success heuristic so valid non-empty extractions are judged correctly.

## Acceptance checklist

- [ ] Reads input from `data/parsed/court_probe/playwright_result_cards_refined.json`.
- [ ] Selects a controlled batch from resolved `text_url_or_action` sentence URLs.
- [ ] Prioritizes direct navigation for detail extraction.
- [ ] Keeps fallback extraction path but not as primary flow.
- [ ] Output detail schema includes:
  - [ ] `case_number`
  - [ ] `decision_date`
  - [ ] `language`
  - [ ] `title_or_issue`
  - [ ] `full_text`
  - [ ] `source_type`
  - [ ] `extracted_from`
  - [ ] `court`
- [ ] Language mapping:
  - [ ] `/zh/ -> zh`
  - [ ] `/pt/ -> pt`
  - [ ] otherwise `unknown`
- [ ] `full_text` validated as non-empty and non-metadata-only.
- [ ] Batch corpus written to `data/parsed/court_probe/playwright_text_details_batch.jsonl`.
- [ ] Batch report written to `data/parsed/court_probe/playwright_text_details_batch_report.txt`.
- [ ] Terminal/report include:
  - [ ] total records attempted
  - [ ] total succeeded
  - [ ] total failed
  - [ ] zh count
  - [ ] pt count
  - [ ] average text length
  - [ ] whether batch extraction appears successful
- [ ] Success heuristic does **not** fail only because `direct_sentence_pages_opened_count == 0`.
- [ ] Success heuristic is based on validated non-empty full-text extractions and acceptable failure ratio.

## Evidence developer must provide

1. Command run for Day 13 batch extractor.
2. Tail/head of generated JSONL confirming required fields.
3. Full report text or key report lines showing required metrics.
4. Day 12 heuristic update evidence (code diff snippet + updated report logic lines).
5. `git status` and commit hash for this round.
