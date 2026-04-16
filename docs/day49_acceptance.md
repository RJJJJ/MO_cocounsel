# Day 49 Acceptance

## Today objective
Keep the current default local model unchanged and expand the local metadata generation sample batch under the fixed best stable prompt.

## Deliverables
- `crawler/metadata/expand_current_default_model_generation_batch.py`
- `crawler/metadata/expand_current_default_model_generation_batch_spec.md`
- `docs/day49_acceptance.md`
- Local acceptance output (do not commit large generated artifact):
  - `data/eval/expanded_current_default_model_generation_batch_report.txt`

## Acceptance checklist
- [ ] Current default model is fixed as `qwen2.5:3b-instruct`.
- [ ] Prompt version is fixed as `day45_prompt_b_tch_norm`.
- [ ] Traditional Chinese normalization remains enabled.
- [ ] Expanded sample batch is larger than earlier small samples and still not full `77` cases.
- [ ] Generation path is based on Day 43/Day 45 local generation flow.
- [ ] Output remains compatible with Day 42 comparison harness schema.
- [ ] Deterministic baseline remains benchmark/fallback reference.
- [ ] Script is local-only (no DB / no cloud API / no vector retrieval).
- [ ] Terminal output includes at least:
  - [ ] current default model used
  - [ ] prompt version fixed
  - [ ] sample cases selected
  - [ ] generation success count
  - [ ] generation total count
  - [ ] field completeness
  - [ ] script normalization applied yes/no
  - [ ] whether expanded current-default batch appears successful
- [ ] Local report includes the same required operational summary.
- [ ] No README changes.
- [ ] No large generated artifacts committed to git diff.

## Evidence developer must provide
1. Command used to run Day 49 expanded batch locally (with parameters).
2. Terminal output snippet showing required summary lines.
3. Local report path and the final success status line.
4. Git diff proving only code/docs were committed.
