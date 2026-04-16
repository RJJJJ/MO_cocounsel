# Day 43 Acceptance

## Today objective

Connect a local Chinese model metadata generation layer that produces Day 38 schema-shaped outputs for Day 42 comparison harness consumption, while keeping deterministic baseline unchanged as benchmark/fallback.

## Deliverables

- `crawler/metadata/connect_local_chinese_model_metadata_generation.py`
  - local-only metadata generation runner
  - configurable local backend + model selection
  - sample-batch execution (3–10 cases) before any full-scale run
  - outputs model-generated metadata JSONL and local report

- `crawler/metadata/local_model_metadata_generation_spec.md`
  - rationale for local model priority
  - benchmark/fallback vs future-primary role split
  - model selection strategy and auditability contract
  - current limitations and recommended next steps

- local output paths (runtime outputs; no large artifacts committed):
  - `data/eval/model_generated_metadata_output.jsonl`
  - `data/eval/local_model_metadata_generation_report.txt`

## Acceptance checklist

- [ ] No vector retrieval work added.
- [ ] No database work added.
- [ ] No cloud model integration added.
- [ ] Local model backend is configurable.
- [ ] Model name is configurable (CLI and/or environment variable).
- [ ] Preferred default model is local `Qwen2.5 7B Instruct` equivalent naming.
- [ ] Sample-batch run supports at least 3–10 cases.
- [ ] Output schema includes:
  - [ ] `core_case_metadata`
  - [ ] `generated_digest_metadata.case_summary`
  - [ ] `generated_digest_metadata.holding`
  - [ ] `generated_digest_metadata.legal_basis`
  - [ ] `generated_digest_metadata.disputed_issues`
  - [ ] `generation_status`
  - [ ] `generation_method = local_model_generated`
  - [ ] `model_name`
  - [ ] `prompt_version`
  - [ ] `provenance_notes`
- [ ] Terminal output includes:
  - [ ] sample cases selected
  - [ ] model-generated cases written
  - [ ] generation fields attempted
  - [ ] whether local model metadata generation appears successful
- [ ] Day 42 harness can directly load the generated model output path.
- [ ] Deterministic baseline remains untouched.
- [ ] README unchanged.
- [ ] No large generated artifacts committed.

## Evidence developer must provide

1. Command(s) run for Day 43 local model generation (sample batch).
2. Terminal output snippet including required summary lines.
3. Path of local outputs generated:
   - `data/eval/model_generated_metadata_output.jsonl`
   - `data/eval/local_model_metadata_generation_report.txt`
4. Optional but recommended: Day 42 comparison harness run command using generated output.
5. Git diff confirmation:
   - code/docs only
   - no large generated artifacts committed.
