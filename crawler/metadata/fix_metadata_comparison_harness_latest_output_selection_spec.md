# Day 53 Spec: Fix Metadata Comparison Harness Latest-Output Selection

## Why this is the next priority
- Metadata generation batch has expanded beyond the earlier 10-case sample, but selection logic in comparison and downstream layers can still bind to stale artifacts.
- This causes misleading model-generated coverage counts and inflated fallback counts.
- Before FastAPI-facing product integration, artifact selection must be deterministic, valid, and shared across all metadata-consuming layers.

## Scope and constraints
- Local-only Python changes.
- No metadata generation algorithm changes.
- No default model changes.
- No candidate-model promotion logic changes.
- No DB / vector retrieval / external API / cloud model integration.

## Artifact selection rules
1. **Explicit path override (highest priority):**
   - If CLI/user passes `--model-metadata <path>` (or comparison `--model-input <path>`) and path is not default sentinel behavior, use it.
   - Fail fast if the explicit path is invalid.
2. **Auto latest fallback:**
   - If path is default or sentinel `latest`, discover candidate model-generated artifacts and choose the latest valid one.
3. **Stable tie-break dimensions:**
   - modified time (primary)
   - naming convention priority
   - report pairing hint

## Validity checks for candidate outputs
A candidate output is valid only if:
- file exists and is a regular file
- JSONL is parseable (line-by-line JSON object)
- schema-compatible enough (contains digest fields in either root or `generated_digest_metadata`)
- distinct case count > 0

## Reporting requirements
The fix report must print:
- selected model metadata output path
- selected model metadata case count
- previous stale path detected (yes/no)
- whether latest-output selection fix appears successful

Comparison harness and downstream layers should also expose selected path + case count in stdout/report diagnostics.

## Downstream components affected
- Metadata comparison harness (`crawler/metadata/build_metadata_generation_comparison_harness.py`)
- Metadata-integrated research pipeline (`crawler/pipeline/integrate_metadata_into_research_pipeline.py`)
- Case-card layer (`crawler/pipeline/build_case_card_ui_ready_output.py`)
- API-ready response envelope (`crawler/pipeline/build_api_ready_response_envelope.py`)
- Shared selection utility (`crawler/metadata/metadata_artifact_selection.py`)

## Recommended next step
- Prepare a FastAPI integration surface that returns the existing API-ready envelope diagnostics (including selected metadata artifact path and case count), **or**
- Expand metadata-integrated pipeline coverage and acceptance scenarios while keeping the same artifact selection utility as the single source of truth.
