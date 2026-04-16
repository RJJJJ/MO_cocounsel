# Day 54 Spec: FastAPI Integration Surface for API-Ready Research Envelope

## Why FastAPI integration surface is now the next stage

Day 52 established a stable API-ready response envelope, and Day 53 stabilized metadata artifact latest-output selection diagnostics across downstream layers. With those foundations in place, the next product step is to expose the existing local research pipeline result through a minimal HTTP backend contract.

This stage focuses on transport integration only:

- keep retrieval and metadata generation behavior unchanged,
- keep envelope structure unchanged,
- keep metadata artifact selection diagnostics visible,
- expose one minimal endpoint suitable for frontend or API consumer integration.

## Endpoint contract

- Method: `POST`
- Path: `/api/research/query`
- Handler behavior:
  1. Accept request payload (`query`, `top_k`).
  2. Call existing Day 52 API-ready envelope builder.
  3. Return envelope payload directly as response model.

No DB calls, cloud model calls, or external API integrations are introduced.

## Request/response schema

### Request schema

```json
{
  "query": "string",
  "top_k": 5
}
```

### Response schema

```json
{
  "schema_version": "v1",
  "query": "string",
  "top_k": 5,
  "result_count": 5,
  "diagnostics": {
    "retrieved_cases_count": 5,
    "case_cards_built": 5,
    "model_generated_metadata_used_count": 4,
    "deterministic_fallback_used_count": 1,
    "success_flag": true,
    "selected_model_metadata_path": "data/eval/expanded_current_default_model_generation_batch_output.jsonl",
    "selected_model_metadata_case_count": 57
  },
  "results": [
    {
      "authoritative_case_number": "...",
      "authoritative_decision_date": "...",
      "court": "...",
      "language": "...",
      "case_type": "...",
      "case_summary": "...",
      "holding": "...",
      "legal_basis": ["..."],
      "disputed_issues": ["..."],
      "metadata_source": "model_generated",
      "pdf_url": "...",
      "text_url_or_action": "...",
      "card_title": "...",
      "card_subtitle": "...",
      "card_tags": ["..."]
    }
  ]
}
```

## Relationship with existing pipeline

FastAPI layer does not replace any existing pipeline steps. It acts as a thin transport surface on top of current local pipeline flow:

`query -> metadata-integrated pipeline -> case-card UI-ready layer -> API-ready response envelope -> FastAPI endpoint response`

The endpoint intentionally reuses the same Day 52 envelope builder so diagnostics and artifact selection source-of-truth remain consistent.

## Current limitations

- Minimal single endpoint only (`POST /api/research/query`).
- No endpoint-level auth, rate limiting, tracing, or request-id fields yet.
- No pagination cursor/offset contract yet.
- No DB-backed persistence.
- No external model or external API integration.

## Recommended next step

Prioritize one of:

1. Add endpoint-level validation and tests (request/response contract, regression guards), or
2. Prepare frontend integration/demo using this stable HTTP contract.
