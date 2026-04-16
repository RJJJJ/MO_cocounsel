# Day 46 Acceptance

## Today objective
Benchmark one upgraded local model candidate against the current working local metadata generation model under controlled, comparable sample-batch conditions.

## Deliverables
- `crawler/metadata/benchmark_upgraded_local_model_candidate.py`
- `crawler/metadata/upgraded_local_model_candidate_benchmark_spec.md`
- `docs/day46_acceptance.md`
- Local acceptance report output path (not committed as large artifact):
  - `data/eval/upgraded_local_model_candidate_benchmark_report.txt`

## Acceptance checklist
- [ ] Benchmark script is local-only and does not call cloud APIs.
- [ ] No database integration.
- [ ] No vector retrieval logic.
- [ ] Current model and candidate model are tested on the same sample cases.
- [ ] Prompt version and other key comparison conditions are held constant.
- [ ] Report includes at least:
  - [ ] `current_model_name`
  - [ ] `candidate_model_name`
  - [ ] `prompt_version`
  - [ ] sample cases used
  - [ ] generation success count
  - [ ] field completeness
  - [ ] comparison-ready yes/no
  - [ ] script normalization applied
  - [ ] basic runtime practicality note
- [ ] Terminal output includes at least:
  - [ ] current model tested
  - [ ] candidate model tested
  - [ ] sample cases processed
  - [ ] current model successful generations
  - [ ] candidate model successful generations
  - [ ] whether upgraded local model candidate benchmark appears successful
- [ ] Deterministic baseline remains benchmark/fallback strategy (not replaced blindly).
- [ ] No large generated artifacts are committed.

## Evidence developer must provide
1. Command used to run benchmark script with parameters.
2. Terminal output snippet showing required benchmark summary lines.
3. The generated local report path and key summary section.
4. Git diff proving only code/docs are submitted (no large generated artifacts).
