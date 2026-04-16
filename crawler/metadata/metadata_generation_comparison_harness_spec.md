# Metadata Generation Comparison Harness Spec (Day 42)

## Why this is now the next priority

Day 38~Day 41 established a stable metadata target schema, deterministic extraction baseline, field evaluation set, and refinement feedback loop. The latest conclusion is that deterministic rule tuning alone is unlikely to close weaker-field quality gaps (`case_summary`, `holding`) in a meaningful way.

So the immediate product need is to create a **comparison harness contract** that can continuously compare:

1. deterministic baseline output (current benchmark)
2. future local-model-generated output (future primary layer)

This enables safe migration to model-based generation while preserving deterministic fallback and regression visibility.

## Role split

- **Deterministic baseline = benchmark + fallback**
  - stable, reproducible, local-only output
  - used for backstop behavior and side-by-side quality checks

- **Model-generated layer = future primary generation layer**
  - expected to improve semantic quality on weak fields
  - initially optional/pending in this round

## Compared fields

The harness compares these digest fields only:

- `case_summary`
- `holding`
- `legal_basis`
- `disputed_issues`

## Comparison contract

Per case, report must include:

- `authoritative_case_number`
- `language`
- field-by-field comparison items:
  - `baseline_value`
  - `model_value`
  - `comparison_status`

Supported status values:

- `match`
- `different`
- `model_missing_field`
- `model_pending` (entire model layer absent for case)
- `baseline_missing_field`

Aggregated summary must include:

- `cases compared`
- `fields compared`
- `fields where model is missing`
- `comparison-ready` (`yes`/`no`)

## Placeholder behavior before model layer is connected

When model output file is absent, harness still runs in placeholder mode:

- baseline data is processed normally
- model side is treated as pending
- report explicitly shows:
  - `baseline available: yes`
  - `model-generated layer pending: yes`
- aggregated summary keeps `comparison-ready: no`

## Recommended next step

Choose one immediate follow-up:

1. Connect a **local Chinese model metadata generation** pipeline and output to the harness contract.
2. Build a **metadata prompt/eval loop** for local model generation, then feed outputs into this harness for iterative comparison.

Both paths should keep deterministic baseline as benchmark/fallback throughout rollout.
