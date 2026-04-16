# Metadata Model Prompt/Eval Loop Spec (Day 47)

## Why current default model remains unchanged

Day 46 benchmark evidence showed the upgraded local candidate has some completeness upside, but runtime cost remains too high for default local-machine promotion. Therefore, **current default local model stays unchanged** in Day 47:

- default model remains `qwen2.5:7b-instruct` for prompt-loop runs,
- deterministic baseline remains benchmark/fallback,
- no model promotion occurs in this round.

## Why prompt refinement is preferred now

Prompt/control quality is the highest-value, lowest-risk improvement point before another promotion attempt:

- keeps local-only constraints intact,
- improves output structure and field signal quality without changing runtime profile,
- preserves like-for-like comparability for a future candidate re-benchmark.

## Day 47 prompt refinement goals

Day 47 introduces a new prompt version (`day47_prompt_a`) and compares it against earlier versions (e.g. `day45_prompt_b_tch_norm`, optionally Day 44 prompts).

Primary goals:

1. **Stronger schema-constrained output instructions**
   - single JSON object only,
   - fixed field names and types,
   - explicit empty-value behavior.
2. **Clearer field-level controls**
   - `case_summary`: shorter and cleaner,
   - `holding`: emphasize dispositive outcome extraction,
   - `legal_basis`: keep only text-grounded legal bases,
   - `disputed_issues`: remove procedural/noisy items.
3. **Traditional Chinese normalization flow preserved**
   - keep script normalization post-processing,
   - retain `script_normalization_applied` and `output_script` signals.
4. **Auditability preserved**
   - keep `model_name`, `prompt_version`, `generation_status`, `script_normalization_applied` in outputs and reports.

## Expected quality improvements

Under the same current default local model, `day47_prompt_a` is expected to:

- reduce verbosity in `case_summary`,
- improve dispositive precision of `holding`,
- reduce noisy entries in `disputed_issues`,
- maintain legal grounding quality in `legal_basis`,
- maintain comparable generation success and comparison-readiness.

## Recommended next step

After Day 47 prompt-loop validation, choose one controlled follow-up:

1. **Re-benchmark upgraded local model candidate** under improved prompt (`day47_prompt_a`) for fair comparison; or
2. **Expand current default local-model metadata generation batch** using the best Day 47 prompt version.

Both follow-ups must remain local-only, avoid cloud APIs, avoid vector retrieval/database changes, and keep deterministic baseline as fallback.
