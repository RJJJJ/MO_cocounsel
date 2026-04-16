# Integrate Metadata into Research Pipeline Spec (Day 50)

## Why metadata integration is now the next stage

The retrieval path, citation binding, and answer synthesis skeleton are already connected and stable in local deterministic mode. Metadata generation assets are also available (target schema, deterministic baseline, and local model outputs).

The next practical product step is to connect those generated metadata records back into the end-to-end research output so each case card is immediately useful for analyst review and UI assembly, while keeping retrieval behavior unchanged.

## Metadata source preference rule

For each retrieved case number:

1. Prefer `model_generated` metadata record when present.
2. Treat model-generated metadata as the primary enrichment source in this stage.

## Fallback rule

When model-generated metadata is unavailable for a retrieved case:

1. Fallback to deterministic baseline metadata (`deterministic_baseline`).
2. If both metadata sources are missing, keep retrieval core fields and emit empty digest fields while still tagging `metadata_source` as `deterministic_baseline` for explicit fallback traceability.

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

- Metadata integration currently enriches retrieval outputs only; no UI rendering layer is added in this round.
- Fallback provenance is binary (`model_generated` vs `deterministic_baseline`) and does not expose per-field source mixing.
- No cloud model, DB, vector retrieval, or candidate-model promotion changes are included.

## Recommended next step

Choose one immediate follow-up:

1. Build a case-card / UI-ready output layer that renders metadata-enriched sources directly.
2. Fix comparison harness latest-output selection logic to reduce manual input-path maintenance during eval loops.
