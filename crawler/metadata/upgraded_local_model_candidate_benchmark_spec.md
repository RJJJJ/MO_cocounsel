# Upgraded Local Model Candidate Benchmark Spec (Day 46)

## Why model candidate benchmarking is now the next priority
After Day 43/44/45, the local metadata generation path is functional, has a prompt/eval loop, and includes Traditional Chinese normalization. The next risk is **assumption-based model switching**. We now need controlled, evidence-based benchmarking so that any upgrade decision is reproducible and reversible, while keeping deterministic baseline as fallback.

## Comparison conditions that must be held constant
To make the benchmark credible, keep these constants fixed across current model and candidate model:

- Same sample batch/case set
- Same prompt version
- Same generation script path and parsing rules
- Same normalization behavior (Traditional Chinese normalization enabled)
- Same backend type (local-only)
- Same timeout and input truncation settings
- No database dependency
- No external API / cloud model

## Evaluation dimensions

### 1) JSON/output stability
- Whether output can be parsed into required JSON structure
- Whether required fields are present consistently across cases
- Whether run has usable generation success rate

### 2) Field completeness
- Coverage counts for:
  - `case_summary`
  - `holding`
  - `legal_basis`
  - `disputed_issues`
- Empty-field frequency and missing-field frequency

### 3) Semantic usefulness
- Outputs should be legally meaningful and concise enough for downstream metadata use
- `legal_basis` and `disputed_issues` should contain case-relevant content when available
- Candidate should not regress on core legal signal quality vs current model

### 4) Runtime practicality
- End-to-end runtime for same sample set
- Approximate per-case latency
- Operational note on whether runtime is practical for local batch usage

## Promotion decision rule
Promote upgraded local model candidate only when all are true:

1. Comparable conditions were held constant.
2. Comparison-ready status is yes.
3. Candidate does not reduce generation success count.
4. Candidate is equal or better on field completeness and output stability.
5. Runtime tradeoff remains operationally acceptable for local usage.

Otherwise keep current model as default and retain deterministic baseline fallback.

## Recommended next step
- **Promote upgraded model candidate** if the decision rule is satisfied.
- **Or keep current default and refine prompt loop further** if candidate fails stability/completeness/runtime thresholds.
