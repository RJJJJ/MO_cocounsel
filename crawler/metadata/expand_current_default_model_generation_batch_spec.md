# Expand Current Default Model Generation Batch Spec (Day 49)

## Why current default is retained
Day 48 re-benchmark shows that the candidate model (`qwen3:4b-instruct`) can improve completeness on some fields, but incurs a larger runtime tradeoff on the current local machine. To preserve operational stability, Day 49 keeps the default unchanged at `qwen2.5:3b-instruct`.

## Why batch expansion is preferred now (instead of immediate promotion)
Immediate promotion is risky when runtime overhead is substantially higher in the same local environment. A safer next step is to expand the current-default generation batch and verify sustained stability, schema consistency, and normalization behavior before switching defaults.

## Fixed conditions
- Current default model: `qwen2.5:3b-instruct`
- Prompt version: `day45_prompt_b_tch_norm`
- Traditional Chinese normalization: enabled
- Deterministic baseline remains benchmark/fallback
- Local-only backend
- No database
- No external/cloud API
- No vector retrieval

## Batch expansion objective
Use the existing Day 43/45 generation path (`connect_local_chinese_model_metadata_generation.py`) to run a larger sample batch than prior small samples, while still below full-set (`77`) execution. Keep output JSONL compatible with comparison harness expectations so Day 42-style comparison can continue without schema drift.

## Current limitations
- This round validates only the retained current-default model, not full candidate re-promotion.
- Results depend on local hardware throughput and local model runtime conditions.
- Expanded batch is still a sample, not full-corpus completion.

## Recommended next step
- Promote upgraded model candidate in a stronger hardware environment where runtime cost is acceptable; **or**
- Run side-by-side current-vs-candidate comparison on a larger batch under fixed prompt and identical truncation/timeout constraints.
