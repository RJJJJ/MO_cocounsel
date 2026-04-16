# Metadata Generation Target Schema Spec (Day 38)

## Why this is the next priority

Day 37 completed route-specific retrieval evaluation slices, which means retrieval/citation/output plumbing is now stable enough to support a higher-value layer: **case-level metadata/digest outputs**.

Defining a stable target schema now is the best next step because it gives downstream components a consistent contract for:

- case cards
- citation cards
- legal research summaries
- future metadata generation pipelines
- future LLM augmentation (later round)

This Day 38 scope is intentionally schema-first, not quality-first generation.

## Scope constraints (Day 38)

- Local-only implementation.
- No database integration.
- No external API calls.
- No LLM calls.
- No vector retrieval additions.
- Focus on schema definition and sample-shaped output only.

## Target schema definition

Each case-level output record is shaped as:

```json
{
  "core_case_metadata": {
    "authoritative_case_number": "string",
    "authoritative_decision_date": "string",
    "court": "string",
    "language": "string",
    "case_type": "string",
    "pdf_url": "string",
    "text_url_or_action": "string",
    "source_chunk_ids": ["string"],
    "source_case_paths": ["string"]
  },
  "generated_digest_metadata": {
    "case_summary": "string",
    "holding": "string",
    "legal_basis": ["string"],
    "disputed_issues": ["string"]
  },
  "generation_status": "string",
  "generation_method": "string",
  "provenance_notes": ["string"]
}
```

## Field meanings

### A. `core_case_metadata`

- `authoritative_case_number`:
  Canonical case number used for case identity and citation joins.
- `authoritative_decision_date`:
  Canonical decision date (as stored in corpus source).
- `court`:
  Court authority label.
- `language`:
  Main judgment language code (e.g., `zh`, `pt`).
- `case_type`:
  Case/procedure type label.
- `pdf_url`:
  Source PDF judgment URL.
- `text_url_or_action`:
  Source text page/action anchor from corpus preprocessing.
- `source_chunk_ids`:
  Chunk IDs contributing evidence for this case-level record.
- `source_case_paths`:
  Local source paths (metadata/full text) to preserve traceability.

### B. `generated_digest_metadata`

- `case_summary`:
  Case-level overall summary text.
- `holding`:
  Judgment outcome / core conclusion oriented statement.
- `legal_basis`:
  Legal basis abstraction (statutory anchors / core legal rationale references).
- `disputed_issues`:
  Issue-focused list of disputed points.

### Cross-cutting provenance/control fields

- `generation_status`:
  Current generation stage marker (e.g., schema demo draft vs validated generation).
- `generation_method`:
  Deterministic/local method tag for reproducibility.
- `provenance_notes`:
  Human-readable notes about constraints and evidence lineage.

## Provenance requirements

For every case-level metadata output, provenance must support local reproducibility:

1. Keep `source_chunk_ids` to trace digest fields back to chunk-level evidence.
2. Preserve source-case paths in `source_case_paths` where available.
3. Include method/status markers to avoid over-claiming generation quality.
4. Record non-LLM deterministic mode in `provenance_notes` during baseline rounds.

## Deterministic now vs future-generation work

### Deterministic now (Day 38)

- Build and freeze target output schema.
- Produce sample-shaped outputs from existing local corpus.
- Use deterministic placeholder extraction logic for digest fields.
- Emit local demo report with field-population and success indicators.

### Future-generation work (not in Day 38)

- Improve summary/holding/legal-basis/issue quality.
- Add robust per-field confidence and validation metrics.
- Add richer legal-basis normalization and cross-case linking.
- Introduce LLM augmentation only after deterministic baseline + evaluation gates are defined.

## Recommended next step

Recommended priority order:

1. **Implement deterministic metadata extraction baseline** (field-level heuristics + reproducible evaluation set).
2. Optionally add a **local dense retrieval stub** after deterministic baseline is measurable.

This sequence keeps quality attribution clear and avoids mixing schema work with generation-method complexity too early.
