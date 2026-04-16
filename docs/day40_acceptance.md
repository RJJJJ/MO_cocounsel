# Day 40 Acceptance

## Today objective

Build a **metadata field evaluation benchmark** and a **local evaluation runner** for the deterministic metadata extraction baseline, focused on:
- `case_summary`
- `holding`
- `legal_basis`
- `disputed_issues`

## Deliverables

- `crawler/metadata/build_metadata_field_evaluation_set.py`
  - local-only builder for small, human-checkable benchmark data
  - outputs `data/eval/metadata_field_evaluation_set.jsonl`

- `crawler/metadata/run_metadata_field_evaluation.py`
  - local-only evaluator against Day 39 deterministic outputs
  - computes coverage and per-field comparison signals
  - outputs `data/eval/metadata_field_evaluation_report.txt`

- `crawler/metadata/metadata_field_evaluation_set_spec.md`
  - explains benchmark rationale, design, scoring, limitations, and next step

## Acceptance checklist

- [ ] Evaluation set JSONL exists and includes 5-10 cases.
- [ ] Evaluation set includes both `zh` and `pt` cases.
- [ ] Every row includes required expected metadata fields.
- [ ] Evaluation runner reads evaluation set + deterministic baseline outputs.
- [ ] Runner reports field coverage.
- [ ] Runner reports exact/normalized overlap for `legal_basis`.
- [ ] Runner reports exact/normalized overlap for `disputed_issues`.
- [ ] Runner reports loose overlap/containment signals for `case_summary` and `holding`.
- [ ] Runner writes local report to `data/eval/metadata_field_evaluation_report.txt`.
- [ ] Terminal summary includes:
  - [ ] cases evaluated
  - [ ] case_summary score summary
  - [ ] holding score summary
  - [ ] legal_basis score summary
  - [ ] disputed_issues score summary
  - [ ] weakest field
  - [ ] whether metadata field evaluation appears successful
- [ ] No DB usage, no external API, no LLM calls.
- [ ] No large generated artifacts committed.

## Evidence developer must provide

1. Commands run:
   - build evaluation set
   - run deterministic baseline (if prediction file absent)
   - run metadata field evaluation

2. Terminal output snippets showing required summary lines.

3. Paths of produced local artifacts:
   - `data/eval/metadata_field_evaluation_set.jsonl`
   - `data/eval/metadata_field_evaluation_report.txt`

4. Git diff review confirming no large generated artifacts were added.
