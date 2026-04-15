# Day 30 Acceptance - Issue Decomposition Layer

## Today objective

Build a deterministic local issue decomposition layer that transforms raw legal queries into structured retrieval-oriented components before retrieval, without introducing database access, external APIs, or LLM-based decomposition.

## Deliverables

1. `crawler/retrieval/issue_decomposition_layer.py`
   - Accepts raw query string input.
   - Produces decomposition output containing:
     - `original_query`
     - `normalized_query`
     - `main_issue`
     - `sub_issues`
     - `query_terms`
     - `retrieval_subqueries`
   - Rule-based and deterministic only.
   - Supports:
     - single legal concept
     - multiple parallel concepts
     - procedure/remedy terms
     - case-number queries
     - mixed legal + fact terms
   - Includes local demo runner and report writer.

2. `crawler/retrieval/issue_decomposition_layer_spec.md`
   - Explains rationale, supported patterns, deterministic strategy, output schema, and integration path.

3. `data/eval/issue_decomposition_demo_report.txt`
   - Local demo output with required acceptance evidence.

## Acceptance checklist

- [ ] Issue decomposition layer is implemented as local-only deterministic logic.
- [ ] No database access added.
- [ ] No external API access added.
- [ ] No LLM calls added.
- [ ] Existing retrieval main flow remains unchanged.
- [ ] Output includes all required fields:
  - `original_query`
  - `normalized_query`
  - `main_issue`
  - `sub_issues`
  - `query_terms`
  - `retrieval_subqueries`
- [ ] `retrieval_subqueries` retains original query.
- [ ] `retrieval_subqueries` includes canonicalized term-driven subqueries.
- [ ] `retrieval_subqueries` is bounded (no explosion).
- [ ] Demo terminal output includes:
  - query received
  - normalized query
  - main issue
  - sub issue count
  - retrieval subquery count
  - whether issue decomposition appears successful
- [ ] No large generated artifacts included in git diff.

## Evidence developer must provide

- Command used to run local decomposition demo.
- Terminal output snippet with the six required lines.
- Path to generated report: `data/eval/issue_decomposition_demo_report.txt`.
- `git status` snippet showing only intended code/doc/report changes.
