# Day 31 Acceptance - Hybrid Retrieval With Issue Decomposition Integration

## Today objective

Integrate the local issue decomposition layer into the hybrid retrieval orchestration so retrieval can fan out over decomposition subqueries and deterministically merge/dedupe results before returning final top-k hits.

## Deliverables

1. `crawler/retrieval/hybrid_retrieval_with_decomposition.py`
   - Accepts:
     - `--query "<text>"`
     - `--top_k <int>`
     - `--decompose on/off`
   - Runs optional decomposition pre-stage.
   - Fans out retrieval over generated subqueries.
   - Merges/dedupes by `chunk_id` deterministically.
   - Preserves retrieval metadata and `retrieval_source`.
   - Emits final merged top-k results including `matched_subqueries`.

2. `crawler/retrieval/hybrid_retrieval_with_decomposition_spec.md`
   - Documents rationale, flow, fan-out strategy, merge/dedupe rules, limitations, and next steps.

3. `data/eval/hybrid_retrieval_with_decomposition_demo_report.txt`
   - Local demo evidence output.

4. `docs/crawling_strategy.md` update
   - Adds explicit observation that `court=all` can be useful for broad coverage/demo but may repeat result windows across pages, so full-scale harvest may need per-court crawling plus later merge/dedup.

## Acceptance checklist

- [ ] Decomposition-aware hybrid retrieval integration is implemented locally.
- [ ] Existing BM25 retriever core behavior is unchanged.
- [ ] No dense retrieval implementation is introduced.
- [ ] No database access added.
- [ ] No external API access added.
- [ ] CLI supports required flags (`--query`, `--top_k`, `--decompose`).
- [ ] Retrieval executes per subquery when decomposition is enabled.
- [ ] Merge/dedupe is deterministic and chunk-id based.
- [ ] Same chunk across subqueries keeps best score and tracked subqueries.
- [ ] Final hit schema includes all required fields plus `matched_subqueries`.
- [ ] Demo terminal output includes:
  - query received
  - decomposition used: on/off
  - subqueries generated count
  - retrieval hits before merge
  - retrieval hits after merge
  - top_k returned
  - whether decomposition-aware retrieval appears successful
- [ ] No large generated artifacts are included in git diff.

## Evidence developer must provide

- Command used to run local Day 31 demo.
- Terminal output snippet with the required seven lines.
- Path to generated report: `data/eval/hybrid_retrieval_with_decomposition_demo_report.txt`.
- `git status` snippet showing only intended code/docs/report changes.
