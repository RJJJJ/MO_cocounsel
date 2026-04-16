# Day 48 Acceptance

## Today objective
Re-benchmark an upgraded local model candidate against the current default local model under fixed best prompt and fixed generation conditions.

## Deliverables
- `crawler/metadata/rebenchmark_upgraded_local_model_candidate.py`
- `crawler/metadata/rebenchmark_upgraded_local_model_candidate_spec.md`
- `docs/day48_acceptance.md`
- Local acceptance output (do not commit large generated artifact):
  - `data/eval/rebenchmark_upgraded_local_model_candidate_report.txt`

## Acceptance checklist
- [ ] Current model is fixed as `qwen2.5:3b-instruct` during re-benchmark.
- [ ] Candidate model is configurable via CLI argument.
- [ ] Prompt version is fixed to `day45_prompt_b_tch_norm`.
- [ ] Same sample batch is enforced for both current and candidate model runs.
- [ ] Same generation script logic is used for both runs.
- [ ] Same Traditional Chinese normalization flow is preserved.
- [ ] Same timeout/input truncation policy is applied.
- [ ] Report contains at least:
  - [ ] `current_model_name`
  - [ ] `candidate_model_name`
  - [ ] `prompt_version`
  - [ ] `sample cases used`
  - [ ] `generation success count`
  - [ ] `field completeness`
  - [ ] `script normalization applied`
  - [ ] `runtime seconds`
  - [ ] `comparison-ready yes/no`
  - [ ] `promotion hint`
- [ ] Terminal output contains at least:
  - [ ] current model tested
  - [ ] candidate model tested
  - [ ] prompt version fixed
  - [ ] sample cases processed
  - [ ] current model successful generations
  - [ ] candidate model successful generations
  - [ ] whether upgraded local model re-benchmark appears successful
- [ ] No README changes.
- [ ] No large generated artifacts committed to git diff.
- [ ] No vector retrieval/database/cloud model integration in this round.

## Evidence developer must provide
1. Command used to run Day 48 re-benchmark locally (with parameters).
2. Terminal output snippet showing required summary lines.
3. Local report path and key decision section.
4. Git diff showing code/docs-focused changes only.
