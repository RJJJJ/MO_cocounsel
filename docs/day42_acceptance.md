# Day 42 Acceptance

## Today objective

Build a local metadata generation comparison harness to compare deterministic baseline metadata with future local-model-generated metadata, while allowing model-layer-pending placeholder operation.

## Deliverables

- `crawler/metadata/build_metadata_generation_comparison_harness.py`
  - local-only comparison runner
  - compares baseline vs optional model-generated metadata
  - field-level comparison contract for:
    - `case_summary`
    - `holding`
    - `legal_basis`
    - `disputed_issues`
  - emits local comparison report

- `crawler/metadata/metadata_generation_comparison_harness_spec.md`
  - why harness is next priority
  - benchmark/fallback vs future primary role split
  - comparison contract and placeholder behavior
  - next-step recommendation for local model integration

- local report output path (not required to be large artifact in git):
  - `data/eval/metadata_generation_comparison_harness_report.txt`

## Acceptance checklist

- [ ] No vector retrieval work added.
- [ ] No database work added.
- [ ] No cloud model integration added.
- [ ] Harness supports deterministic baseline input.
- [ ] Harness supports optional model-generated input.
- [ ] If model output is absent, runner still succeeds in placeholder mode.
- [ ] Per-case output includes case number, language, and field-by-field comparison.
- [ ] Aggregated summary includes:
  - [ ] cases compared
  - [ ] fields compared
  - [ ] fields where model is missing
  - [ ] comparison-ready yes/no
- [ ] Terminal output includes:
  - [ ] baseline cases loaded
  - [ ] model-generated cases loaded
  - [ ] comparable cases count
  - [ ] model-missing count
  - [ ] whether metadata generation comparison harness appears successful
- [ ] No large generated artifacts committed.
- [ ] README unchanged.

## Evidence developer must provide

1. Commands run:
   - deterministic baseline generation command (if baseline input did not already exist)
   - metadata generation comparison harness command

2. Terminal output snippet containing required summary lines.

3. Path of local comparison report:
   - `data/eval/metadata_generation_comparison_harness_report.txt`

4. Git diff confirmation:
   - code/docs only
   - no large generated artifacts committed.
