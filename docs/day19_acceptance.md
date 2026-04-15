# Day 19 Acceptance - Raw Corpus Storage Layout

## Today objective

Convert Day 18 extracted Macau Court sentence text records into a normalized, durable raw corpus storage layout that supports long-term storage and clean future pagination append workflows.

## Deliverables

- `crawler/storage/build_raw_corpus_layout.py`
- `crawler/storage/raw_corpus_layout_spec.md`
- `docs/day19_acceptance.md`
- Generated outputs from the builder:
  - `data/corpus/raw/macau_court_cases/manifest.jsonl`
  - `data/corpus/raw/macau_court_cases/cases/.../metadata.json`
  - `data/corpus/raw/macau_court_cases/cases/.../full_text.txt`
  - `data/corpus/raw/macau_court_cases/raw_corpus_build_report.txt`

## Acceptance checklist

- [ ] Reads input file:
  - `data/parsed/court_probe/playwright_text_details_from_selector_cards.jsonl`
- [ ] Creates normalized raw corpus directory tree under:
  - `data/corpus/raw/macau_court_cases/`
- [ ] Writes one `metadata.json` and one `full_text.txt` per corpus record.
- [ ] `full_text.txt` stores body text only in UTF-8.
- [ ] Applies authority rules:
  - `authoritative_case_number = detail_case_number else source_list_case_number`
  - `authoritative_decision_date = detail_decision_date else source_list_decision_date`
- [ ] Creates `manifest.jsonl` with key lookup fields.
- [ ] Handles slug safety and empty-value fallback (`unknown_case_<index>`).
- [ ] Produces `raw_corpus_build_report.txt`.
- [ ] Terminal output includes:
  - total records read
  - total corpus records written
  - zh records written
  - pt records written
  - records with authoritative case number
  - records with authoritative decision date
  - whether raw corpus layout build appears successful
- [ ] No database usage.
- [ ] No chunking / embedding / indexing work in this day.

## Evidence developer must provide

- Command executed to run Day 19 builder script.
- Terminal output snippet showing required summary counters.
- Count verification command(s), e.g.:
  - number of manifest lines
  - number of `metadata.json` files
  - number of `full_text.txt` files
- Sample paths from both language partitions when available (`zh`, `pt`).
- Pointer to `raw_corpus_build_report.txt` confirming success status.
