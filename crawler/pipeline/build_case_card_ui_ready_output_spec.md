# Day 51 Spec: Case-Card / UI-Ready Output Layer

## Why UI-ready case cards are the next stage

Day 50 already integrated metadata into retrieval outputs, but the output is still primarily pipeline-oriented. For product and demo value, the next immediate step is an output-shaping layer that transforms enriched case objects into **case-card records** that can be consumed by:

- future frontend rendering,
- API response envelopes,
- demo scripts and acceptance flows.

This stage does not change retrieval truth or metadata provenance; it standardizes presentation shape and card-level fields.

## Scope

- local-only Python formatter layer
- no database integration
- no external API
- no cloud model calls
- no frontend page implementation
- output shaping only

## Case-card schema

Each UI-ready case card record must include:

- `authoritative_case_number`
- `authoritative_decision_date`
- `court`
- `language`
- `case_type`
- `case_summary`
- `holding`
- `legal_basis`
- `disputed_issues`
- `metadata_source`
- `pdf_url`
- `text_url_or_action`
- `card_title`
- `card_subtitle`
- `card_tags`

## Card title / subtitle / tags design

### `card_title`

Goal: immediate scan value in compact list views.

Proposed composition (stable and deterministic):

- `<authoritative_case_number>｜<case_type>｜<court>`
- fallback title if all empty: `未命名案例`

### `card_subtitle`

Goal: compact provenance + context line.

Proposed composition:

- `<language> · <authoritative_decision_date> · metadata:<metadata_source>`

This keeps source traceability visible even in condensed UI cards.

### `card_tags`

Goal: support quick filtering/chips in future UI.

Tag strategy:

- base tags: `case_type`, `language`, `metadata_source`
- optional legal basis highlights: up to first 2 items, prefixed as `basis:<value>`

## Metadata source traceability

- `metadata_source` remains a first-class field in every case card.
- `card_subtitle` repeats source marker in user-visible compact text.
- The layer never rewrites factual values; it only maps enriched fields into UI-ready structure.

## Local report contract

Report path:

- `data/eval/case_card_ui_ready_output_report.txt`

Terminal output must include at least:

- query received
- retrieved cases count
- case cards built
- model-generated metadata used count
- deterministic fallback used count
- whether case-card UI-ready output appears successful

## Current limitations

- `authoritative_decision_date` is derived from retrieval hits and may be empty if retrieval records lack the field.
- `card_tags` are deterministic but shallow; no ontology normalization yet.
- No response envelope versioning (`schema_version`, `request_id`) yet.
- No frontend rendering and no sorting/pagination behavior contract yet.

## Recommended next step

One of the following should be prioritized next:

1. **Build API-ready response envelope** around case-card array (request metadata, paging, diagnostics), or
2. **Fix metadata comparison harness latest-output selection logic** to guarantee stable and newest local artifact selection before downstream formatting.
