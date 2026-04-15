# Day 20 Acceptance

## Today objective
Extend Macau court pagination coverage (page 1 to page 10) and append newly discovered cases into the existing raw corpus layout without changing storage contract.

## Deliverables
- `crawler/pipeline/extend_corpus_pagination_range.py`
- `crawler/pipeline/extend_corpus_pagination_range_spec.md`
- `data/corpus/raw/macau_court_cases/manifest.jsonl` updated by append
- `data/corpus/raw/macau_court_cases/cases/` appended with new case folders
- `data/corpus/raw/macau_court_cases/pagination_extension_report.txt`

## Acceptance checklist
- [ ] Script uses Playwright and starts from real search flow.
- [ ] Script selects `中級法院` and submits search before paginating.
- [ ] Script attempts pagination pages 1..10 unless early clear stop condition triggers.
- [ ] Selector-driven card parsing is used.
- [ ] Detail extraction follows `text_url_or_action` and extracts body-first text.
- [ ] Existing `manifest.jsonl` is read before writing.
- [ ] Duplicate check uses:
  - `authoritative_case_number`
  - `authoritative_decision_date`
  - `language`
  - `court`
- [ ] Duplicate records are skipped and counted.
- [ ] New records are appended to corpus layout + manifest.
- [ ] Report file is generated with key counters.
- [ ] Terminal output includes key counters and success flag.
- [ ] No DB/chunking/embedding/indexing added.

## Evidence developer must provide
1. Terminal output excerpt showing:
   - pages attempted
   - valid pages parsed
   - cards discovered
   - detail pages attempted
   - detail pages succeeded
   - duplicates skipped
   - new corpus records added
   - whether pagination extension appears successful
2. A brief note on stop condition observed (or max page reached).
3. Paths of newly added case folders under `data/corpus/raw/macau_court_cases/cases/`.
4. Confirmation that `manifest.jsonl` was append-updated.
5. Path to generated report file.
