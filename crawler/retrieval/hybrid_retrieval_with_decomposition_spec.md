# Hybrid Retrieval With Decomposition Spec (Day 31)

## Why integrating decomposition is now the next priority

Day 27 established a stable hybrid retrieval skeleton (BM25 active), while Day 30 proved a deterministic local issue decomposition layer can generate structured retrieval subqueries. The highest-leverage integration step now is connecting them so multi-issue legal queries can fan out retrieval coverage before downstream citation binding and answer synthesis.

## Orchestration flow

1. Receive raw query.
2. Optionally run issue decomposition (`--decompose on/off`).
3. Build deterministic `retrieval_subqueries`:
   - decomposition on: use decomposer output, keep order, dedupe in order.
   - decomposition off: single subquery = original query.
4. For each subquery, call existing hybrid retrieval flow (currently BM25-active).
5. Merge and dedupe hit lists by `chunk_id`.
6. Return final top-k merged hits.

## Merge / dedupe rules

- Deduplicate by `chunk_id`.
- Preserve `retrieval_source` and all citation-ready metadata fields.
- If the same `chunk_id` appears in multiple subqueries:
  - keep one merged hit,
  - keep the best score,
  - append subquery text into `matched_subqueries` (deduped, stable order).
- Final rank ordering is deterministic:
  - primary key: score descending,
  - tie-breaker: `chunk_id` ascending.

## Subquery fan-out strategy

- Default mode is decomposition on.
- Fan-out list uses deterministic bounded subqueries produced by Day 30 decomposer.
- In-order uniqueness is enforced to prevent duplicate retrieval calls.
- Retrieval budget is constrained by running each subquery with the same `top_k` budget and merging later.

## Output hit schema (merged)

Each returned hit includes:

- `chunk_id`
- `score`
- `retrieval_source`
- `authoritative_case_number`
- `authoritative_decision_date`
- `court`
- `language`
- `case_type`
- `chunk_text_preview`
- `pdf_url`
- `text_url_or_action`
- `matched_subqueries`

## Current limitations

- BM25 is the only active retriever.
- No dense retrieval execution yet.
- No database integration.
- No external API calls.
- No LLM planning/reasoning layer.

## Recommended next step

Pick one:

1. Connect Day 28 citation binding + Day 29 answer synthesis to this integrated decomposition-aware retrieval flow.
2. Add a local dense retrieval stub and test deterministic fusion with decomposition fan-out.
