# Day 61 Acceptance - Retrieval Regression Pack Baseline

## Today objective

Build a re-runnable, comparable Day 61 retrieval regression pack on top of the current authoritative merged Macau court corpus, so Day 62+ retrieval strengthening can be measured against a fixed baseline.

## Deliverables

1. `retrieval/eval/day61_regression_queries.json`
   - Day 61 regression query pack with fixed demo queries and broader coverage.
2. `retrieval/eval/run_day61_regression_pack.py`
   - Runner that reuses current router/retrieval pipeline and evaluates pass rules.
3. `retrieval/eval/day61_regression_pack_spec.md`
   - Design rationale, principles, and limitations.
4. Regression outputs produced by the runner:
   - `data/eval/day61_regression_results.json`
   - `data/eval/day61_regression_summary.txt`

## Acceptance checklist

- [ ] Query pack contains required fixed demo queries:
  - [ ] `假釋`
  - [ ] `量刑過重`
  - [ ] `253/2026`
- [ ] Query pack includes additional high-value queries (5-10).
- [ ] Coverage includes:
  - [ ] exact case number lookup
  - [ ] single legal concept
  - [ ] harder concept phrasing / variants
  - [ ] Portuguese or mixed query (>=1-2)
- [ ] Each query contains required fields:
  - [ ] `query_id`
  - [ ] `query_text`
  - [ ] `route_hint` (nullable)
  - [ ] `expected_behavior`
  - [ ] `expected_case_numbers` or `expected_match_notes`
  - [ ] `pass_rule`
- [ ] Runner prints at least:
  - [ ] total queries
  - [ ] passed
  - [ ] failed
  - [ ] pass rate
  - [ ] per-query top results summary
  - [ ] failure reasons
- [ ] Runner writes both required output files under `data/eval/`.
- [ ] No dense retrieval / fusion / reranker introduced.
- [ ] No crawler / corpus / API / frontend refactor introduced.

## Exact commands to run

```bash
python retrieval/eval/run_day61_regression_pack.py
```

Optional explicit-path run:

```bash
python retrieval/eval/run_day61_regression_pack.py \
  --query-pack retrieval/eval/day61_regression_queries.json \
  --output-json data/eval/day61_regression_results.json \
  --output-summary data/eval/day61_regression_summary.txt
```

## Evidence developer must provide

1. Terminal output of the regression run showing total/passed/failed/pass rate.
2. Snippet of per-query top results summary and failure reasons (if any).
3. Generated artifacts:
   - `data/eval/day61_regression_results.json`
   - `data/eval/day61_regression_summary.txt`
4. Confirmation that constraints were respected (no dense/fusion/reranker and no API/frontend contract change).
