# Day 44 Acceptance

## Today objective

Build a repeatable local prompt/eval loop for metadata generation across sample cases, enabling prompt-version comparison now and model-candidate comparison later.

## Deliverables

- `crawler/metadata/build_metadata_model_prompt_eval_loop.py`
  - orchestrates Day 43 local metadata generation on sample batches
  - supports prompt version A/B comparison on the same local model
  - supports future extensibility with multiple local model names
  - runs local evaluation/comparison steps and aggregates loop summary

- `crawler/metadata/metadata_model_prompt_eval_loop_spec.md`
  - explains why prompt/eval loop is the next priority
  - documents prompt versioning strategy and sample workflow
  - clarifies relationship with Day 42 comparison harness
  - describes model promotion implications and next-step options

- local report output path (runtime/local acceptance output):
  - `data/eval/metadata_model_prompt_eval_loop_report.txt`

## Acceptance checklist

- [ ] No vector retrieval work added.
- [ ] No database work added.
- [ ] No cloud model integration added.
- [ ] Loop supports sample case selection.
- [ ] Loop supports prompt version A/B comparison on same model.
- [ ] Loop remains local-only and reuses existing Day 43 path.
- [ ] Loop integrates existing comparison harness and field evaluation tooling.
- [ ] Loop report contains, per run:
  - [ ] `model_name`
  - [ ] `prompt_version`
  - [ ] sample cases used
  - [ ] generation success count
  - [ ] fields generated
  - [ ] evaluation-ready yes/no
  - [ ] comparison-ready yes/no
- [ ] Terminal output includes:
  - [ ] prompt versions evaluated
  - [ ] sample cases processed
  - [ ] successful generations
  - [ ] comparison runs completed
  - [ ] whether metadata model prompt/eval loop appears successful
- [ ] README unchanged.
- [ ] No large generated artifacts committed.

## Evidence developer must provide

1. Command(s) used to run Day 44 loop on sample batch.
2. Terminal output snippet containing required summary lines.
3. Path to local report output:
   - `data/eval/metadata_model_prompt_eval_loop_report.txt`
4. Confirmation that diff contains code/docs only and excludes large generated artifacts.
