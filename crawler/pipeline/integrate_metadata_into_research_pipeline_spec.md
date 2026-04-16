# Integrate Metadata into Research Pipeline Spec (Day 50 + Day 59 policy alignment)

## Why metadata integration is a post-merge stage

Retrieval path, citation binding, answer synthesis skeleton, and metadata artifacts are already available. After Day 59, authoritative corpus assembly is explicitly defined as per-court crawl -> merge/dedupe. Therefore metadata attachment should target this authoritative merged corpus stage instead of per-court crawl-time attachment.

## Authoritative timing rule

```text
per-court crawl
-> merge/dedupe authoritative corpus
-> downstream retrieval/prep consumption
-> metadata attachment
```

This ordering reduces ambiguity and prevents per-court partial metadata state from being mistaken as final authority.

## Metadata source preference rule

For each retrieved case number from authoritative merged corpus:

1. Prefer `model_generated` metadata record when present.
2. Treat model-generated metadata as the primary enrichment source in this stage.

## Fallback rule

When model-generated metadata is unavailable for a retrieved case:

1. Fallback to deterministic baseline metadata (`deterministic_baseline`).
2. If both metadata sources are missing, keep retrieval core fields and emit empty digest fields while still tagging `metadata_source` as `deterministic_baseline` for explicit fallback traceability.

Deterministic baseline must remain available as fallback/benchmark/regression guard.

## Model policy guardrail

- Default local model policy remains unchanged in this stage (`qwen2.5:3b-instruct`).
- No model experimentation/promotion is part of Day 59 corpus assembly.

## Enriched output schema

Each case card / research source item includes at least:

- `authoritative_case_number`
- `court`
- `language`
- `case_type`
- `case_summary`
- `holding`
- `legal_basis`
- `disputed_issues`
- `metadata_source`
  - `model_generated`
  - `deterministic_baseline`
- `pdf_url`
- `text_url_or_action`

Top-level run summary includes:

- `query_received`
- `retrieved_cases_count`
- `cases_enriched_with_metadata`
- `model_generated_metadata_used_count`
- `deterministic_fallback_used_count`
- `metadata_integrated_research_pipeline_appears_successful`

## Current limitations

- Metadata integration enriches retrieval outputs only; no UI rendering layer is added here.
- Fallback provenance is binary (`model_generated` vs `deterministic_baseline`) and does not expose per-field source mixing.
- No cloud model, DB, vector retrieval, or candidate-model promotion changes are included.
- A dedicated full-corpus retrieval regression pack for Day 59 authoritative corpus is still pending.

## Recommended Day 60 next step

Build full-corpus retrieval eval + regression pack on top of the Day 59 authoritative merged corpus artifacts.
