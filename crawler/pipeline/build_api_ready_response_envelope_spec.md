# Day 52 Spec: API-Ready Response Envelope on Top of Case-Card Layer

## Why API-ready envelope is now the next stage

Day 51 already produced UI-ready case-card records, which are ideal for rendering but still missing a stable API contract wrapper. The next product step is to add a response envelope that:

- carries schema versioning,
- exposes request-level fields (`query`, `top_k`),
- includes diagnostics counters for observability,
- and transports Day 51 case cards in `results` unchanged.

This improves backend/frontend integration readiness without touching retrieval ranking or metadata generation behavior.

## Scope

- local-only Python shaping layer
- no DB integration
- no external API calls
- no cloud model calls
- no retrieval logic change
- no metadata generation logic change

## Envelope schema

Top-level fields:

- `schema_version`: response contract version (current: `v1`)
- `query`: query received by pipeline
- `top_k`: top-k requested
- `result_count`: number of records in `results`
- `diagnostics`: execution counters and success status
- `results`: Day 51 case-card records (pass-through)

Illustrative shape:

```json
{
  "schema_version": "v1",
  "query": "...",
  "top_k": 5,
  "result_count": 5,
  "diagnostics": {
    "retrieved_cases_count": 5,
    "case_cards_built": 5,
    "model_generated_metadata_used_count": 4,
    "deterministic_fallback_used_count": 1,
    "success_flag": true
  },
  "results": [
    { "authoritative_case_number": "...", "...": "..." }
  ]
}
```

## Diagnostics fields

`diagnostics` includes at least:

- `retrieved_cases_count`
- `case_cards_built`
- `model_generated_metadata_used_count`
- `deterministic_fallback_used_count`
- `success_flag`

`success_flag` is inherited from Day 51 case-card output success assessment so Day 52 remains purely a wrapper stage.

## Relationship with case-card layer

- Day 52 **calls** Day 51 `build_case_card_ui_ready_output`.
- Day 52 **does not mutate** case-card record fields.
- Day 52 **adds envelope context** only (version, request fields, diagnostics, result count).

So the pipeline becomes:

`query -> metadata-integrated pipeline -> case-card layer -> API-ready envelope`

## Current limitations

- No request id / trace id yet.
- No pagination cursor fields yet.
- No API transport server (FastAPI) is introduced in this round.
- Success semantics are still tied to Day 51 record completeness checks.

## Recommended next step

Prioritize one of:

1. fix metadata comparison harness latest-output selection logic, or
2. prepare FastAPI integration surface to serve this envelope contract directly.
