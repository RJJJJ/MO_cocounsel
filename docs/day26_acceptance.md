# Day 26 Acceptance - Chinese Legal Query Normalization

## Today objective

Improve Chinese legal query-side normalization for the local BM25 retrieval baseline and rerun local retrieval evaluation with before/after comparison.

## Deliverables

- `crawler/retrieval/improve_chinese_legal_query_normalization.py`
  - Local deterministic Chinese legal query normalization layer.
- `crawler/retrieval/local_bm25_query_prototype.py`
  - Optional integration for query normalization.
- `crawler/eval/run_local_retrieval_eval.py`
  - Baseline + normalized mode comparison report flow.
- `crawler/retrieval/chinese_legal_query_normalization_spec.md`
  - Rules, rationale, limitations, and next-step recommendation.
- `data/eval/macau_court_query_test_set.jsonl`
  - Fix obvious expected-case labeling gap for case-number lookup.
- Local generated output (not to be committed as large artifact):
  - `data/eval/macau_court_eval_report_normalized.txt`

## Acceptance checklist

- [ ] No vector retrieval added.
- [ ] No external service dependency introduced.
- [ ] No database changes introduced.
- [ ] README unchanged.
- [ ] Query normalization includes:
  - [ ] Unicode normalization
  - [ ] full-width/half-width normalization
  - [ ] punctuation normalization
  - [ ] case-number normalization
  - [ ] legal phrasing variant handling
  - [ ] legal synonym/variant mapping
  - [ ] simple high-value Chinese legal query expansion
- [ ] Local eval can run baseline and normalized-query mode.
- [ ] Evaluation output includes:
  - [ ] normalization strategy used
  - [ ] total queries evaluated
  - [ ] baseline hit@k
  - [ ] normalized hit@k
  - [ ] whether normalized retrieval appears improved
- [ ] case_number_lookup queries no longer contain obvious `expected_case_numbers=[]` labeling misses.

## Evidence developer must provide

- Commands run (evaluation and checks).
- Terminal summary showing baseline vs normalized hit@k.
- Path to generated report file:
  - `data/eval/macau_court_eval_report_normalized.txt`
- Git diff summary proving only code/docs/test-set updates were committed and no large generated artifacts were added.
