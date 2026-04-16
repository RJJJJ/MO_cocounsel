# Traditional Chinese Normalization in Model-Generated Metadata (Day 45)

## Why Traditional Chinese normalization is now required

Day 43 established local-model metadata generation, and Day 44 validated a repeatable prompt/eval loop. However, generated Chinese fields can still contain Simplified Chinese characters, which introduces inconsistency for Macau legal research output. Because downstream output is expected to be Traditional Chinese-first in this domain, script normalization is now required as a post-generation control in the local metadata flow.

## Fields normalized

The post-generation Traditional Chinese normalization step applies to model-generated digest fields only:

- `case_summary`
- `holding`
- `disputed_issues` (each list item)
- `legal_basis` Chinese description portions (list items are normalized in a script-safe way)

## Structured fields that must not be mutated

The normalization layer must not mutate structured/source identity fields, including:

- case number fields (e.g., `authoritative_case_number`)
- URLs (`pdf_url`, `text_url_or_action`)
- `source_chunk_ids`
- other structured metadata fields under `core_case_metadata`

## Placement in generation flow

Normalization is a post-generation step between:

1. local model output parse/sanitize
2. JSONL write to model-generated metadata output

Flow summary:

1. Build prompt from selected sample cases.
2. Generate metadata using local-only model backend.
3. Parse JSON and sanitize target fields.
4. Normalize generated Chinese fields to Traditional Chinese.
5. Add audit/control fields:
   - `script_normalization_applied`
   - `output_script`
6. Write output records and generation report.

## Current limitations

- Normalization depends on local environment support:
  - prefers local OpenCC when available
  - falls back to a minimal local Simplified→Traditional map
- Fallback conversion is intentionally conservative and may miss rare or context-sensitive conversions.
- This step normalizes script style, but does not guarantee legal semantic quality; prompt/model quality still governs extraction quality.

## Recommended next step

Choose one of the following next steps:

1. Benchmark an upgraded local model candidate on the expanded Day 45 sample batch to improve extraction quality while retaining Traditional Chinese normalization controls.
2. Run the existing metadata generation comparison harness on the expanded batch to compare prompt/model variants with normalization-enabled outputs.
