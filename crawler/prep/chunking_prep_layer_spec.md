# Day 21 Chunking Prep Layer Spec (Macau Court Corpus)

## Why chunking prep is now the next priority
After Day 17-20, the pipeline has reached stable corpus acquisition (selector-driven parsing, detail extraction, raw corpus layout, and pagination extension). The current bottleneck shifts from crawling completeness to retrieval readiness. We now need a deterministic normalization and chunking preparation layer so later retrieval/indexing work can proceed on stable text units.

## Metadata authority rules (post detail-metadata rollback)
Because `detail_case_number`, `detail_decision_date`, and `detail_title_or_issue` were removed as unreliable, metadata authority should follow:

1. **Primary authority:** selector-driven result-page fields persisted in manifest (`authoritative_case_number`, `authoritative_decision_date`, `court`, language, source URLs).
2. **Secondary authority:** stored corpus metadata fields that come from the result-page pipeline (e.g., `source_list_case_type`).
3. **Detail page role:** full text body source and traceable source links (`pdf_url`, `text_url_or_action`), not authoritative structured metadata.

## Chunking strategy
The chunking prep layer intentionally uses a conservative, stable baseline:

- Apply lightweight text normalization:
  - normalize line endings,
  - collapse repeated inline whitespace,
  - remove excessive blank lines,
  - preserve legal text content and ordering.
- Split text using **paragraph-aware** accumulation first.
- If paragraph boundaries are unavailable or a paragraph is too long, fallback to **fixed-size** chunking.
- Use deterministic chunk IDs based on authoritative metadata + chunk index + chunk text digest.

## Chunk record schema
Each output record in `chunks.jsonl` includes:

- `authoritative_case_number`
- `authoritative_decision_date`
- `court`
- `language`
- `case_type`
- `chunk_id`
- `chunk_index`
- `chunk_text`
- `source_metadata_path`
- `source_full_text_path`
- `pdf_url`
- `text_url_or_action`

## Assumptions and limitations
- This layer does **not** perform embedding, indexing, or database writes.
- `case_type` availability depends on metadata quality in raw corpus metadata files.
- Chunking is character-length based for stability and simplicity; no model-token counting yet.
- No semantic heading-aware chunking is applied in this baseline version.

## Recommended next step
Choose one of:

1. Build a **BM25 prep/index layer** on top of `chunks.jsonl` for lexical retrieval baseline.
2. Expand crawling coverage to **multi-court** corpus while reusing this chunking-prep contract.
