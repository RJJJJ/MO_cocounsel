# Day 22 BM25 Prep Layer Spec (Macau Court Chunk Corpus)

## Why BM25 prep is the next priority
Day 21 completed stable chunk preparation for the Macau court corpus (`chunks.jsonl`), giving us deterministic chunk units with source traceability. The next practical retrieval milestone is a lexical baseline that is simple, transparent, and cheap to run locally. BM25-ready text preparation gives immediate retrieval value before adding embedding, reranking, or database infrastructure.

## BM25 text normalization strategy
This baseline keeps normalization conservative and deterministic:

1. Start from `chunk_text` already cleaned during Day 21.
2. Apply Unicode NFKC normalization for consistent character forms.
3. Normalize line endings and lowercase text.
4. Remove punctuation/symbol noise while preserving:
   - CJK ranges,
   - Latin alphanumerics,
   - whitespace boundaries.
5. Collapse repeated whitespace to single spaces and trim.

Output behavior:
- `chunk_text` is preserved unchanged for display and citation.
- `bm25_text` stores normalized lexical text used for BM25-style indexing/querying.

## Preserved traceability fields
Each BM25 prep record carries required retrieval-display and source-tracing metadata:

- `chunk_id`
- `authoritative_case_number`
- `authoritative_decision_date`
- `court`
- `language`
- `case_type`
- `chunk_text`
- `bm25_text`
- `source_metadata_path`
- `source_full_text_path`
- `pdf_url`
- `text_url_or_action`

This keeps every retrieval hit traceable back to the prepared chunk and original raw-source artifacts.

## Assumptions and limitations
- No embedding/vector indexing is performed in this layer.
- No database integration is performed in this layer.
- No external tokenization services are required; normalization is regex-based and local.
- Chinese segmentation is not introduced yet; BM25 behavior for CJK is baseline lexical matching and may be improved later with optional local tokenization.
- Quality depends on Day 21 chunk quality and source metadata completeness.

## Recommended next step
Choose one immediate follow-up:

1. Build a local BM25 query prototype on top of `bm25_chunks.jsonl` to validate retrieval quality and citation rendering.
2. Expand crawling coverage to additional courts (multi-court corpus) and reuse the same BM25 prep contract.
