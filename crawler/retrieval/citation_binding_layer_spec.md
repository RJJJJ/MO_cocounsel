# Citation Binding Layer Spec (Day 28)

## Why citation binding is the next priority

Day 27 established a working local hybrid retrieval skeleton with a stable hit schema and BM25 active path. The next highest-value step is to make retrieval output immediately usable by downstream legal answer generation. In a legal research product, answers must be citation-ready and auditable; therefore binding retrieval hits into deterministic citation records is higher priority than introducing dense retrieval at this stage.

## Scope

- Local-only transformation layer.
- No database integration.
- No external API calls.
- No modifications to the existing hybrid retrieval main flow.
- Input: Day 27 `RetrievalHit` records.
- Output: citation-ready records for answer assembly.

## Citation record schema

Each citation record includes:

- `chunk_id`
- `citation_label`
- `authoritative_case_number`
- `authoritative_decision_date`
- `court`
- `language`
- `case_type`
- `pdf_url`
- `text_url_or_action`
- `chunk_text_preview`
- `retrieval_source`
- `score`
- `source_rank`
- `source_group_key`

## Citation label design

Recommended format:

- `<court>｜<case_number>｜<decision_date>`

Example:

- `澳門法院｜757/2025｜26/03/2026`

Design goals:

- Human-readable in citation cards and inline references.
- Stable enough for reproducible local demos.
- Compatible with multilingual retrieval metadata.

If a component is empty, the binder falls back to `unknown` for that segment to keep label shape stable.

## Source grouping / rank fields

- `source_rank`
  - 1-indexed rank following current retrieval order (top hit = 1).
  - Useful for answer synthesis priority and UI ordering.

- `source_group_key`
  - Deterministic grouping key: `<court>::<case_number>::<decision_date>::<retrieval_source>`.
  - Supports grouping multiple chunks from the same case and source.
  - Enables future dedup and case-level citation card aggregation.

## Integration with future answer generation

The citation binding layer plugs in immediately after retrieval and before answer synthesis:

1. Query enters hybrid retrieval.
2. Top-k `RetrievalHit` list returned.
3. Citation binder transforms hits into `CitationRecord` list.
4. Answer synthesis consumes citation records to:
   - attach inline citations,
   - build citation cards,
   - keep evidence traces per statement.

Because the binder is local and deterministic, it can be tested independently from generation models.

## Recommended next step

Either of the following can be the Day 29 direction:

1. Add a local dense retrieval stub that emits compatible `RetrievalHit` records for fusion testing.
2. Build an answer synthesis skeleton that consumes citation-ready records and outputs structured answer drafts with evidence links.
