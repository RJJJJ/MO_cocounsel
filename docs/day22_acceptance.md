# Day 22 Acceptance - BM25 Prep Layer

## Today objective
Build a BM25 preparation layer that converts Day 21 prepared chunks into lexical-retrieval-ready records while preserving source traceability metadata.

## Deliverables
- `crawler/prep/build_bm25_prep_layer.py`
- `crawler/prep/bm25_prep_layer_spec.md`
- Runtime output only (do not commit):
  - `data/corpus/prepared/macau_court_cases/bm25_chunks.jsonl`
  - `data/corpus/prepared/macau_court_cases/bm25_prep_report.txt`

## Acceptance checklist
- [ ] Script reads `data/corpus/prepared/macau_court_cases/chunks.jsonl`.
- [ ] Script writes BM25-ready JSONL output to `bm25_chunks.jsonl`.
- [ ] Script writes prep summary report to `bm25_prep_report.txt`.
- [ ] Each BM25 record includes required fields:
  - [ ] `chunk_id`
  - [ ] `authoritative_case_number`
  - [ ] `authoritative_decision_date`
  - [ ] `court`
  - [ ] `language`
  - [ ] `case_type`
  - [ ] `chunk_text`
  - [ ] `bm25_text`
  - [ ] `source_metadata_path`
  - [ ] `source_full_text_path`
  - [ ] `pdf_url`
  - [ ] `text_url_or_action`
- [ ] `chunk_text` is preserved separately from normalized BM25 text.
- [ ] No embedding/vector/db logic is added.
- [ ] Terminal output includes:
  - [ ] total chunks read
  - [ ] total bm25 records written
  - [ ] zh records count
  - [ ] pt records count
  - [ ] average bm25_text length
  - [ ] bm25 prep success indicator

## Evidence developer must provide
1. Command used to run BM25 prep script.
2. Terminal summary lines showing all required BM25 aggregate metrics.
3. Confirmation that runtime artifacts were generated locally and are excluded from git diff/commit.
4. Short note confirming no embedding/vector/database functionality was added in Day 22.
