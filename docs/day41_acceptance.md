# Day 41 Acceptance

## Today objective

Improve deterministic metadata extraction rules based on Day 40 field-level evaluation, with priority order:
1. `case_summary`
2. `holding`

And then rerun local metadata field evaluation to verify whether improvements are effective without adding retrieval/database/LLM infrastructure.

## Deliverables

- `crawler/metadata/improve_deterministic_metadata_extraction_rules.py`
  - local-only improved deterministic extractor
  - targeted rule refinement for summary/holding quality
  - outputs improved prediction JSONL + local report

- `crawler/metadata/improved_metadata_extraction_rules_spec.md`
  - rationale for Day 41 prioritization
  - per-field rule changes
  - expected effects, limitations, and recommended next step

- local evaluation rerun output (not required in git diff):
  - `data/eval/metadata_field_evaluation_report_improved.txt`

## Acceptance checklist

- [ ] No vector retrieval work added.
- [ ] No database work added.
- [ ] No LLM integration added.
- [ ] `case_summary` rules were explicitly refined (boundary, stop, fallback quality).
- [ ] `holding` rules were explicitly refined (dispositive sentence selection).
- [ ] `legal_basis` / `disputed_issues` quality not materially regressed.
- [ ] Metadata field evaluation rerun locally against improved predictions.
- [ ] Terminal output includes:
  - [ ] cases evaluated
  - [ ] improved case_summary score summary
  - [ ] improved holding score summary
  - [ ] legal_basis score summary
  - [ ] disputed_issues score summary
  - [ ] whether metadata extraction rule improvement appears successful
- [ ] No large generated artifacts committed.
- [ ] README unchanged.

## Evidence developer must provide

1. Commands run:
   - improved deterministic extraction script
   - metadata field evaluation runner against improved predictions

2. Terminal output snippet containing required summary lines.

3. Path of local improved evaluation report:
   - `data/eval/metadata_field_evaluation_report_improved.txt`

4. Git diff confirmation:
   - only code/docs changes
   - no large generated artifact committed.
