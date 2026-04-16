## Model selection strategy

A configurable local Chinese-capable instruct model is required because:

1. deployment environments may have different local model availability,
2. quality/speed tradeoffs vary by machine,
3. product evolution may require stronger local variants without rewriting pipeline code,
4. candidate models should be benchmarked before promotion into the primary generation path.

### Required model policy

- local-only model backend
- no cloud API and no hosted model endpoint
- backend and model name must be configurable
- generated outputs must preserve model-specific auditability for comparison

### Current baseline default

- `Qwen3 8B`
- role: current stable benchmark model for local metadata generation connection

### Current upgrade candidates

- `Qwen3 14B` (if local hardware/runtime permits)
- `Qwen2.5 14B Instruct`
- other local Chinese-capable instruct models already available in environment

### Promotion rule

A candidate local model should only replace the current default after comparison against the existing baseline on:

- JSON format stability
- metadata field completeness
- case_summary quality
- holding fidelity
- legal_basis usefulness
- disputed_issues usefulness
- local runtime practicality

## Model evaluation and promotion policy

The local model layer is configurable by design.

This means:

- the project does not assume one permanent model forever,
- new candidate local Chinese models may be tested,
- promotion to default model should be benchmark-driven rather than assumption-driven.

### Current policy

- `Qwen3 8B` remains the current baseline default
- candidate outputs should be compared through the existing metadata comparison harness before changing defaults

### Minimum upgrade checks

Before a new model is promoted, it should be tested on a sample batch and checked for:

- valid JSON output rate
- field coverage rate
- semantic usefulness of generated metadata
- lower obvious hallucination / vague filler rate
- acceptable runtime on local hardware

## Current limitations

- sample-batch operation first; not full-corpus generation yet
- prompt optimization is intentionally minimal in this round
- model availability/performance depends on local runtime environment
- failed generations are recorded with fallback empty field payloads and failure status
- different local models may produce meaningfully different metadata style/quality even under the same prompt
- model upgrade should not bypass comparison-harness-based evaluation

## Recommended next step

Pick one immediate follow-up:

1. run Day 42 comparison harness with the current baseline default model output,
2. run the same sample batch with an upgrade candidate,
3. compare both outputs before changing default model policy,
4. then build a dedicated prompt/eval loop for metadata fields if upgrade looks promising.

Deterministic baseline should remain benchmark/fallback throughout.