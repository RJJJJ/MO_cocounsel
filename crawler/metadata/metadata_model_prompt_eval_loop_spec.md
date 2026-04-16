# Metadata Model Prompt/Eval Loop Spec (Day 44)

## Why prompt/eval loop is now the next priority

Day 42 delivered a comparison harness and Day 43 connected a local Chinese-capable model generation path. The immediate gap is repeatability: we need a stable way to test prompt changes on the same sample cases before scaling generation or changing default models.

A prompt/eval loop is the fastest control point for improving generated metadata quality while preserving:

- local-only execution,
- deterministic benchmark comparability,
- auditable model/prompt provenance,
- low-cost iteration on sample batches.

## Prompt versioning strategy

Use explicit prompt version IDs (for example `day44_prompt_a`, `day44_prompt_b`) and attach them to every model-generated record. Minimum policy:

1. each run must declare one `model_name` and one `prompt_version`,
2. each output record must retain `model_name` and `prompt_version`,
3. prompt changes should bump version IDs instead of mutating old labels,
4. A/B comparisons should keep sample-case selection fixed whenever possible.

This makes future model-candidate comparisons possible without losing prompt lineage.

## Sample-batch evaluation workflow

1. Select sample cases (`--sample-case-limit` and/or `--case-numbers`).
2. Run local generation for prompt A using Day 43 path.
3. Run local generation for prompt B using the same sample strategy.
4. For each prompt run:
   - capture generation success count,
   - capture per-field population (`case_summary`, `holding`, `legal_basis`, `disputed_issues`),
   - run metadata field evaluation report generation when eval set is available,
   - run Day 42 comparison harness against deterministic baseline.
5. Write one aggregate Day 44 loop report summarizing run-level and overall readiness.

## Relationship with comparison harness

Day 44 loop does not replace Day 42 harness. It orchestrates Day 43 generation and Day 42 comparison in repeatable batches.

- Day 42 remains the canonical baseline-vs-model structural comparison surface.
- Day 44 adds prompt-centric iteration logic and aggregates readiness signals.
- Day 40 field evaluation remains an optional quality signal used by the loop when evaluation set is present.

## Model promotion implications

Prompt and model should be decoupled:

- first, find stronger prompt versions on a fixed local model,
- then compare model candidates under controlled prompt settings.

Promotion implications:

- a model should not be promoted only because it is newer,
- promotion should require stable generation success, improved field usefulness, and comparison readiness,
- promotion decisions should be grounded in Day 44 loop evidence.

## Recommended next step

Choose one immediate next step after Day 44:

1. **Expand local model metadata generation batch** using the best prompt version identified by Day 44; or
2. **Benchmark an upgraded local model candidate** with the same prompt/eval loop settings for like-for-like comparison.

Both paths should stay local-only and continue avoiding full-corpus generation until sample-batch metrics stabilize.
