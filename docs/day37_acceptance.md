# Day 37 Acceptance - Route-Specific Evaluation Slices

## Today objective

Upgrade local retrieval evaluation so quality is reported by deterministic route/query class instead of only a global aggregate.

## Deliverables

- `crawler/eval/integrate_route_specific_eval_slices.py`
  - Reads local query test set.
  - Routes each query with deterministic search router.
  - Captures `query_type`, `routing_strategy`, `retrieval_mode`.
  - Executes current local retrieval path selected by routing.
  - Computes exact-case hit and hit@k.
  - Aggregates required route-specific/query-class slices.
  - Writes local report to `data/eval/route_specific_eval_report.txt`.
  - Prints terminal summary including:
    - total queries evaluated
    - number of slices reported
    - weakest slice
    - strongest slice
    - whether route-specific slicing appears successful

- `crawler/eval/route_specific_eval_slices_spec.md`
  - Motivation for route-specific evaluation priority.
  - Slice definitions.
  - Routing-output-to-evaluation mapping.
  - Small-sample limitations.
  - Next-step recommendation (dense stub or metadata/digest schema).

## Acceptance checklist

- [ ] Local-only implementation (no DB, no external API).
- [ ] No vector retrieval added.
- [ ] Evaluation slicing/reporting only.
- [ ] Required slices are present:
  - [ ] case_number_lookup
  - [ ] single_legal_concept
  - [ ] multi_issue_legal_query
  - [ ] mixed_fact_legal_query
  - [ ] portuguese_or_mixed
  - [ ] ambiguous_or_noisy
- [ ] Per-slice fields include:
  - [ ] total queries
  - [ ] queries with expected cases
  - [ ] exact case hit count
  - [ ] hit@k
  - [ ] small-sample note
- [ ] No README modification.
- [ ] No large generated artifacts committed.

## Evidence developer must provide

1. Command used to run Day 37 evaluator.
2. Terminal output containing all required summary lines.
3. Report path confirmation (`data/eval/route_specific_eval_report.txt`).
4. Diff summary showing only code/docs changes and no large generated artifact additions.
