# Day 63B Acceptance

## today objective

Upgrade dense baseline from `chargram_hash_v1` to `bge-m3` on refreshed chunk-level inputs derived from latest `macau_court_cases_full`, then rerun dense regression and compare against Day 63 / BM25+.

## deliverables

1. Dense-ready chunk refresh script from full corpus source.
2. Day 63B bge-m3 dense build script and artifact path.
3. Day 63B dense regression runner using Day 61 query pack.
4. Comparison report: Day 63B dense vs Day 63 dense vs BM25+.
5. Day 63B upgrade spec document.

## acceptance checklist

- [ ] Source of truth is latest `macau_court_cases_full`.
- [ ] Retrieval unit remains chunk-level (not whole-case-only main path).
- [ ] New dense baseline uses bge-m3 only.
- [ ] Dense embedding text includes metadata + chunk text fields.
- [ ] Day 63B dense artifacts paths are explicit and reproducible.
- [ ] Day 61 regression pack is executed against Day 63B dense-only mode.
- [ ] Outputs generated:
  - [ ] `data/eval/day63b_dense_retrieval_results.json`
  - [ ] `data/eval/day63b_dense_retrieval_summary.txt`
  - [ ] `data/eval/day63b_dense_vs_baselines_comparison.txt`
- [ ] No Day 64 fusion/reranking/API/frontend changes.

## exact commands to run

```bash
python crawler/prep/build_day63b_dense_ready_chunks.py
python retrieval/indexing/build_day63b_bge_m3_dense_index.py
python retrieval/eval/run_day63b_dense_regression.py --rebuild-index
python retrieval/eval/build_day63b_dense_vs_baselines_comparison.py
```

## evidence developer must provide

1. Terminal output of the four commands above.
2. Pass/fail counts and pass rate from Day63B dense regression.
3. Per-query summary + failure reasons from Day63B summary output.
4. Comparison conclusion on whether Day63B is sufficient dense signal for Day64 fusion under BM25 exact-match guardrails.
