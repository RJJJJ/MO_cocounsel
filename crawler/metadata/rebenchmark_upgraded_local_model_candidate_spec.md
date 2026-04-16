# Re-benchmark Upgraded Local Model Candidate Spec (Day 48)

## Why re-benchmarking is now preferred over batch expansion
Day 47 prompt-loop evidence indicates `day45_prompt_b_tch_norm` remains more stable than `day47_prompt_a`. Given prompt stability is not the current bottleneck, the next highest-value step is a fair model-to-model re-benchmark under held-constant conditions instead of expanding prompt variants first.

## Current default model source of truth
- Current default local model: `qwen2.5:3b-instruct`
- Current best prompt version: `day45_prompt_b_tch_norm`
- Re-benchmark script: `crawler/metadata/rebenchmark_upgraded_local_model_candidate.py`

## Fixed benchmark conditions
To keep the comparison fair and promotion-safe, both runs must use:
- Same sample batch (candidate run uses exact case numbers selected in current-model run)
- Same prompt version: `day45_prompt_b_tch_norm`
- Same generation script logic: `connect_local_chinese_model_metadata_generation.py`
- Same Traditional Chinese normalization flow
- Same timeout and input truncation policy
- Same local-only backend category
- No database / no vector retrieval / no cloud API

## Promotion decision criteria
Recommend promoting upgraded candidate only if all conditions are met:
1. `comparison-ready yes/no` is `yes`
2. Candidate generation success count is not lower than current model
3. Candidate field completeness is equal or better overall
4. Runtime remains practical for local batch operation

If any of the above fail, keep current default unchanged.

## Recommended next step
- **Promote upgraded model candidate** when criteria above are satisfied and acceptance checks pass.
- **Or keep current default and expand batch** when evidence is inconclusive or candidate regresses on stability/completeness/runtime.
