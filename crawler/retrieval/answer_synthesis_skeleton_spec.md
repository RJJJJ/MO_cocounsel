# Answer Synthesis Skeleton Spec (Day 29)

## Why answer synthesis is now the next priority

Day 27 delivered a local hybrid retrieval skeleton and Day 28 delivered a citation binding layer. We now already have retrieval hits and citation-ready records, so the next highest-value step is a deterministic answer draft layer that is auditable and directly grounded in retrieved evidence.

This allows product and retrieval teams to validate end-to-end legal research output structure before introducing dense retrieval or any LLM-based generation.

## Scope

- Local-only synthesis logic.
- No database access.
- No external API calls.
- No LLM calls.
- No changes to the retrieval or citation binding main flow.
- Input:
  - `HybridRetrievalResult` hits from the hybrid retrieval skeleton.
  - `CitationRecord` entries from the citation binding layer.
- Output:
  - deterministic structured legal research draft.

## Deterministic draft-generation strategy

1. Receive raw query.
2. Call the existing hybrid retrieval skeleton.
3. Call the existing citation binding layer.
4. Build answer draft using deterministic templates only:
   - Provisional summary generated from query + top source labels + hit count.
   - Key findings assembled from chunk previews (top 3-5 records).
   - Cited source list directly mapped from citation records.
   - Source notes explicitly declare non-LLM / non-final nature.

No inferential legal conclusions beyond retrieved text are introduced.

## Answer draft schema

- `query`
- `answer_type` = `structured_research_draft`
- `provisional_summary`
- `key_findings` (list of objects)
  - `finding_text`
  - `citation_labels` (at least one label per finding)
- `cited_sources` (list of objects)
  - `citation_label`
  - `chunk_id`
  - `pdf_url`
  - `text_url_or_action`
- `source_notes` (optional list)

## Citation usage rules

- Every finding must reference at least one `citation_label`.
- `cited_sources` preserves citation binding values without mutation for:
  - `citation_label`
  - `chunk_id`
  - `pdf_url`
  - `text_url_or_action`
- Source ordering follows retrieval/binder rank order for determinism.
- Duplicate `chunk_id` entries are deduplicated in `cited_sources` to avoid redundant cards.

## Limitations without LLM

- No issue decomposition or multi-issue legal reasoning.
- No narrative synthesis across conflicting authorities.
- No confidence calibration beyond retrieval rank/score.
- Summary and findings are template-driven and may read mechanical.
- Output is not legal advice and should be reviewed by legal professionals.

## Recommended next step

Choose one immediate extension while preserving deterministic evaluability:

1. Add local dense retrieval stub with the same `RetrievalHit` contract to exercise fusion behavior.
2. Add issue decomposition layer (rule-based) before synthesis to better structure multi-issue legal questions.
