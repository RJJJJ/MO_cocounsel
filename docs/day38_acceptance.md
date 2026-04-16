# Day 38 Acceptance - Metadata-Generation Target Schema

## Today objective

Define a stable target schema for case-level metadata/digest output so MO_cocounsel can later support case cards, citation cards, legal research summaries, and future metadata generation/LLM augmentation.

## Deliverables

- `crawler/metadata/build_metadata_generation_target_schema.py`
  - Local-only script.
  - Reads local prepared chunk corpus.
  - Builds target schema record with:
    - `core_case_metadata`
    - `generated_digest_metadata`
    - `generation_status`
    - `generation_method`
    - `provenance_notes`
  - Generates 2-3 sample case outputs in schema shape.
  - Writes local demo report to `data/eval/metadata_generation_target_schema_demo_report.txt`.
  - Prints terminal summary lines including:
    - sample cases processed
    - target fields populated count
    - whether metadata-generation target schema build appears successful

- `crawler/metadata/metadata_generation_target_schema_spec.md`
  - Why metadata target schema is next priority.
  - Schema and field definitions.
  - Provenance requirements.
  - Deterministic-now vs future-generation boundary.
  - Recommended next step.

- `docs/day38_acceptance.md`
  - Day objective, deliverables, acceptance checklist, evidence requirements.

## Acceptance checklist

- [ ] Local-only implementation.
- [ ] No DB integration.
- [ ] No external API integration.
- [ ] No LLM integration.
- [ ] No vector retrieval changes.
- [ ] Target schema includes:
  - [ ] `core_case_metadata`
  - [ ] `generated_digest_metadata`
  - [ ] `generation_status`
  - [ ] `generation_method`
  - [ ] `provenance_notes`
- [ ] `core_case_metadata` includes required fields:
  - [ ] `authoritative_case_number`
  - [ ] `authoritative_decision_date`
  - [ ] `court`
  - [ ] `language`
  - [ ] `case_type`
  - [ ] `pdf_url`
  - [ ] `text_url_or_action`
  - [ ] `source_chunk_ids`
  - [ ] `source_case_paths` (if available)
- [ ] `generated_digest_metadata` includes required fields:
  - [ ] `case_summary`
  - [ ] `holding`
  - [ ] `legal_basis`
  - [ ] `disputed_issues`
- [ ] Demo report generated locally and kept lightweight.
- [ ] README not modified.
- [ ] No large generated artifact committed.

## Evidence developer must provide

1. Command used to run Day 38 schema demo script.
2. Terminal output containing all required summary lines.
3. Report path confirmation (`data/eval/metadata_generation_target_schema_demo_report.txt`).
4. Diff summary showing only code/docs + lightweight local demo output.
