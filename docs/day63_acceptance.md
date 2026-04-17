# Day 63 Acceptance - Dense Retrieval Baseline

## Today objective
Build a reproducible dense retrieval baseline over the existing authoritative merged + prepared Macau court chunk corpus, without replacing BM25 path and without introducing fusion/reranking.

## Deliverables
- Dense baseline implementation:
  - `crawler/retrieval/dense_embedding_baseline.py`
- Dense artifact build script:
  - `retrieval/indexing/build_day63_dense_index.py`
- Dense regression runner:
  - `retrieval/eval/run_day63_dense_regression.py`
- Dense baseline spec:
  - `retrieval/eval/day63_dense_baseline_spec.md`
- Evaluation outputs:
  - `data/eval/day63_dense_retrieval_results.json`
  - `data/eval/day63_dense_retrieval_summary.txt`
  - `data/eval/day63_dense_vs_bm25_comparison.txt`

## Acceptance checklist
- [ ] Dense path reads current prepared chunk corpus.
- [ ] Dense path builds reusable local artifact with embeddings.
- [ ] Day 61 regression query pack can run against dense baseline.
- [ ] Dense eval outputs include totals, pass/fail, pass rate, per-query top hits, failure reasons.
- [ ] Dense vs BM25 comparison summary is produced.
- [ ] BM25 path remains untouched as default retrieval-first strength zone (especially exact case-number lookups).
- [ ] No fusion/reranker/API/frontend changes in Day 63 scope.

## Exact commands to run
```bash
python retrieval/indexing/build_day63_dense_index.py
python retrieval/eval/run_day63_dense_regression.py --rebuild-index
python retrieval/eval/run_day61_regression_pack.py
```

## Evidence developer must provide
- Console logs for the three commands above.
- `day63_dense_retrieval_results.json` and `day63_dense_retrieval_summary.txt` with pass/fail details.
- `day63_dense_vs_bm25_comparison.txt` documenting:
  - pass-rate delta
  - dense-better and bm25-better slices
  - exact case-number behavior under dense
  - concept / harder phrasing / pt-mixed behavior
  - known limitations
  - explicit statement that Day 63 is baseline-only and Day 64 is fusion.
