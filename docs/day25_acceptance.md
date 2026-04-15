# Day 25 Acceptance

## Today objective

Add a reusable local evaluation/query test set and a simple local evaluation runner for the Macau court BM25 retrieval prototype, so retrieval changes can be measured instead of guessed.

## Deliverables

1. `crawler/eval/build_query_test_set.py`
   - builds local JSONL query test set from local BM25 corpus;
   - covers required query categories:
     - 中文法律概念詞,
     - 中文爭點/事實詞,
     - 案件編號查詢,
     - 葡文或中葡混合,
     - 可疑/模糊查詢.

2. `crawler/eval/run_local_retrieval_eval.py`
   - loads query test set;
   - invokes existing local BM25 query prototype components;
   - evaluates each query at top-k;
   - writes local report to `data/eval/macau_court_eval_report.txt`.

3. `crawler/eval/local_retrieval_eval_spec.md`
   - rationale and scope for local retrieval evaluation baseline.

4. local output (not committed as large artifact)
   - `data/eval/macau_court_query_test_set.jsonl`
   - `data/eval/macau_court_eval_report.txt`

## Acceptance checklist

- [ ] Does not modify README.
- [ ] No vector retrieval added.
- [ ] No database integration added.
- [ ] Query test set persisted as JSONL at `data/eval/macau_court_query_test_set.jsonl`.
- [ ] Each test row includes:
  - [ ] `query_id`
  - [ ] `query`
  - [ ] `query_type`
  - [ ] `expected_case_numbers`
  - [ ] `notes`
  - [ ] optional `expected_language`
- [ ] Query set includes all required query categories.
- [ ] Evaluation runner reads query set and BM25 corpus locally only.
- [ ] Evaluation runner output includes:
  - [ ] total queries loaded
  - [ ] total queries evaluated
  - [ ] hit@k summary
  - [ ] whether local retrieval evaluation appears successful
- [ ] No large generated artifacts are committed in diff.

## Evidence developer must provide

1. command used to build test set, e.g.:
   - `python crawler/eval/build_query_test_set.py`
2. command used to run evaluation, e.g.:
   - `python crawler/eval/run_local_retrieval_eval.py --top-k 10`
3. terminal summary containing at least:
   - total queries loaded,
   - total queries evaluated,
   - hit@k summary,
   - whether local retrieval evaluation appears successful.
4. report file path confirmation:
   - `data/eval/macau_court_eval_report.txt`
5. `git status` evidence showing no large generated artifacts included in commit.
