# Day 61 Retrieval Regression Pack Spec

## Why Day 61 focuses on regression instead of more crawling

Day 61 is positioned after authoritative corpus harvesting, per-court convergence crawling, merge, and dedupe are already completed and accepted as baseline. The highest-leverage next step is therefore **retrieval stability measurement** rather than additional ingestion work. This gives Day 62+ retrieval strengthening work a fixed comparison target and avoids mixing data-shape drift with retrieval-quality changes.

## Regression design principles

1. **Re-runnable and deterministic enough for engineering iteration**
   - Inputs are committed (`day61_regression_queries.json`).
   - Evaluation rules are explicit (`pass_rule`) and machine-checkable.
2. **Practical pass criteria instead of fragile rank-locking**
   - Exact case-number lookups may require rank-1 or top-k inclusion.
   - Concept queries use top-k containment against an acceptable case family.
3. **Reuse current retrieval architecture**
   - Runner reuses deterministic router + existing retrieval flows.
   - No dense retrieval, no fusion upgrade, no reranker.
4. **Actionable failure output**
   - Per-query top-hit summaries plus explicit failure reasons are emitted.

## Query coverage design

The Day 61 pack includes:

- Required fixed demo queries:
  - `假釋`
  - `量刑過重`
  - `253/2026`
- Additional high-value queries to cover:
  - exact case lookup variants (`案件編號 187/2026`)
  - single legal concepts (`緩刑`)
  - harder / multi-issue phrasing (`詐騙 集團 量刑`, `無罪推定 證據不足`)
  - Portuguese and mixed-language slices (`recurso suspensão da execução da pena`, `indemnização dano moral 澳門`, `葡文 判決 上訴 期間`)

## Pass/fail philosophy

- **Exact lookup queries**: strict enough to detect serious regressions (rank-1 or top-3 inclusion).
- **Concept queries**: tolerant to minor ranking movement; success is based on target-family containment in top-k.
- **Failure reason quality**: every failed query should explain expected rule vs observed top results.

This balances sensitivity (catch real regressions) and robustness (avoid false alarms from benign ranking permutations).

## How this pack is used in Day 62+ comparisons

1. Run baseline Day 61 pack on the current branch.
2. Apply one retrieval change (e.g., query normalization tweak, routing tweak).
3. Re-run the same pack.
4. Compare:
   - pass rate delta
   - failed query set changes
   - per-query top-hit movement on critical slices (exact case number, Portuguese/mixed)

This supports incremental retrieval strengthening without touching corpus baseline.

## Known limitations

- Pass rules still use curated case-family expectations, so they are not full relevance-judgment sets.
- Some concept queries can legitimately map to multiple legal subtopics; top-k containment is a proxy, not full semantic evaluation.
- The current retrieval stack is BM25-first and sparse-only, so certain semantic variants may remain under-retrieved by design.
- This pack does not measure answer synthesis quality; it evaluates retrieval-stage behavior only.
