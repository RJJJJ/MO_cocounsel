# Day 23 Acceptance - Local BM25 Query Prototype

## Today objective
Build a local-only BM25 query prototype for the prepared Macau court chunk corpus, with explicit tokenizer behavior for Chinese and mixed Chinese/Portuguese legal text, and with traceable top-k retrieval output.

## Deliverables
- `crawler/retrieval/local_bm25_query_prototype.py`
- `crawler/retrieval/local_bm25_query_prototype_spec.md`
- `docs/day23_acceptance.md`
- Runtime output only (do not commit):
  - `data/corpus/prepared/macau_court_cases/bm25_query_demo_report.txt`

## Acceptance checklist
- [ ] Prototype reads input from `data/corpus/prepared/macau_court_cases/bm25_chunks.jsonl`.
- [ ] CLI accepts:
  - [ ] query string
  - [ ] optional `top_k`
- [ ] Local deterministic tokenizer is implemented and not whitespace-only.
- [ ] Tokenization explicitly addresses:
  - [ ] Chinese legal text (CJK-friendly strategy)
  - [ ] Portuguese/Latin-script legal text
  - [ ] mixed alphanumeric legal references
- [ ] Tokenizer strategy used for current run is explicitly reported.
- [ ] Ranking output includes for each hit:
  - [ ] `chunk_id`
  - [ ] `authoritative_case_number`
  - [ ] `authoritative_decision_date`
  - [ ] `court`
  - [ ] `language`
  - [ ] `case_type`
  - [ ] `chunk_text preview`
  - [ ] `pdf_url`
  - [ ] `text_url_or_action`
- [ ] Terminal output includes:
  - [ ] total BM25 records loaded
  - [ ] tokenizer strategy used
  - [ ] query received
  - [ ] top_k returned
  - [ ] success indicator
- [ ] Basic top-level error handling exists.
- [ ] No vector retrieval implementation is added.
- [ ] No database integration is added.
- [ ] No web API integration is added.
- [ ] Large generated artifacts are excluded from git diff/commit.

## Evidence developer must provide
1. Command used to run the local BM25 query prototype.
2. Terminal summary lines showing required query-run metrics.
3. Sample top-k hits showing traceable metadata fields in output.
4. Confirmation that `bm25_query_demo_report.txt` was generated locally (if run) and excluded from commit.
5. Short note confirming no vector/database/API retrieval layer was added in Day 23.
