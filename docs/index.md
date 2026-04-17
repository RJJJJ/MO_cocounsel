# Documentation Index (Focused Refresh)

This index is the fastest entry point for project handoff and ongoing maintenance.

## 1) Start here (project governance + current status)

- `README.md` — repo-level overview, architecture, milestones, runbook.
- `docs/project_status_snapshot.md` — current stage, completed/in-progress milestones, blockers, next action.
- `docs/repo_navigation.md` — where each directory fits in authoritative flow.
- `docs/dependencies_and_runtime.md` — dependency map, runtime requirements, known blockers.

## 2) Source-of-truth and authoritative flow

- `docs/crawling_strategy.md` — per-court convergence, merge/dedupe, post-merge metadata rationale.
- `docs/day59_acceptance.md`, `docs/day59a_acceptance.md`, `docs/day60_acceptance.md`, `docs/day60_hotfix_acceptance.md` — authoritative flow evolution.
- `crawler/storage/raw_corpus_layout_spec.md` — raw/full corpus layout spec.

## 3) Retrieval specs and eval docs (Day 61+)

- `retrieval/eval/day61_regression_pack_spec.md`
- `retrieval/eval/day62_bm25_strengthening_spec.md`
- `retrieval/eval/day63_dense_baseline_spec.md`
- `retrieval/eval/day63b_dense_upgrade_spec.md`
- Acceptance docs:
  - `docs/day61_acceptance.md`
  - `docs/day62_acceptance.md`
  - `docs/day63_acceptance.md`
  - `docs/day63b_acceptance.md` (currently in-progress checkpoint)

## 4) Metadata policy and evaluation

- `crawler/metadata/metadata_generation_target_schema_spec.md`
- `crawler/metadata/deterministic_metadata_extraction_baseline_spec.md`
- `crawler/metadata/metadata_model_prompt_eval_loop_spec.md`
- `crawler/metadata/expand_current_default_model_generation_batch_spec.md`
- `crawler/metadata/fix_metadata_comparison_harness_latest_output_selection_spec.md`

## 5) Historical acceptance trail

- `docs/day1_acceptance.md` ... `docs/day63b_acceptance.md` provide timeline evidence.
- Some older docs reflect historical assumptions and should be read as historical context, not current architecture authority.
