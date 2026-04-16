# Local Model Metadata Generation Spec (Day 43)

## Why this is now the next priority

Day 38~Day 42 already established:

- target metadata output schema,
- deterministic extraction baseline,
- field-level evaluation set,
- comparison harness between baseline and model-generated metadata.

The immediate next step is to connect an actual **local model generation path** so the comparison harness can move from placeholder mode into real side-by-side evaluation on the same cases.

## Role split

- **Deterministic baseline = benchmark/fallback**
  - stable and reproducible
  - no model dependency
  - safety backstop when model generation is unavailable

- **Local model layer = future primary generation layer**
  - expected to improve semantic quality of digest fields
  - currently connected in sample-batch mode first

## Model selection strategy

A configurable local Chinese-capable instruct model is required because:

1. deployment environments may have different local model availability,
2. quality/speed tradeoffs vary by machine,
3. product evolution may require stronger local variants without rewriting pipeline code.

### Required model policy

- local-only model backend
- no cloud API and no hosted model endpoint
- backend and model name must be configurable

### Preferred default

- `Qwen2.5 7B Instruct` (local, instruct-tuned, Chinese capable)

### Acceptable stronger local variants

- `Qwen2.5 14B Instruct`
- other local Chinese-capable instruct models already available in environment

## Input selection strategy (sample-batch first)

This round prioritizes **running path reliability** over full 77-case generation.

- default path uses prepared case chunks (`bm25_chunks.jsonl`)
- case-level text is formed by concatenating selected chunks
- optional filtering:
  - language filter (default `zh`)
  - explicit case-number list
- sample batch target: typically 3–10 cases

Full-text-only mode can be added later if needed, but selected chunk text is enough to validate schema contract + comparison compatibility.

## Output contract

Each generated JSONL record must keep Day 38-compatible shape:

- `core_case_metadata`
- `generated_digest_metadata`
  - `case_summary`
  - `holding`
  - `legal_basis`
  - `disputed_issues`
- `generation_status`
- `generation_method = local_model_generated`
- `model_name`
- `prompt_version`
- `provenance_notes`

Primary local output paths:

- `data/eval/model_generated_metadata_output.jsonl`
- `data/eval/local_model_metadata_generation_report.txt`

## Required audit fields

Every output record must include:

- `model_name`
- `prompt_version`
- `generation_status`

This keeps model-result provenance traceable when comparing against baseline and during later prompt/eval iteration.

## Current limitations

- sample-batch operation first; not full-corpus generation yet
- prompt optimization is intentionally minimal in this round
- model availability/performance depends on local runtime environment
- failed generations are recorded with fallback empty field payloads and failure status

## Recommended next step

Pick one immediate follow-up:

1. run Day 42 comparison harness directly with generated local model output,
2. build a dedicated prompt/eval loop for metadata fields and iterate quality against Day 40 evaluation set.

Both follow-ups should keep deterministic baseline as benchmark/fallback.
