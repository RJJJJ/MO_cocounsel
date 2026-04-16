# Day 55 Spec: Endpoint Validation and Tests for `POST /api/research/query`

## Why this is the next priority

Day 54 exposed the FastAPI integration surface and response envelope.  
Before frontend integration, the HTTP contract must be stable and explicit so clients can rely on deterministic request/response behavior.

This round therefore focuses on:

- endpoint-level request validation hardening
- response contract assertions
- regression protection through local tests

This is intentionally **not** a retrieval/model behavior change round.

## Request validation rules

For `POST /api/research/query`:

- `query` is required
- `query` must be non-empty after trimming whitespace
- `top_k` defaults to `5` when omitted
- `top_k` must be an integer `>= 1`
- invalid/missing fields return FastAPI validation error status (`422`)

## Response contract assertions

Successful responses (`200`) must contain:

- `schema_version`
- `query`
- `top_k`
- `result_count`
- `diagnostics`
- `results`

`diagnostics` must include at least:

- `retrieved_cases_count`
- `case_cards_built`
- `model_generated_metadata_used_count`
- `deterministic_fallback_used_count`
- `success_flag`

## Regression protection scope

The Day 55 tests protect:

- transport contract of the FastAPI endpoint
- schema-level request constraints
- stable presence of response envelope fields used by downstream consumers

Out of scope for this round:

- retrieval ranking changes
- metadata generation behavior changes
- database or cloud model integration

## Recommended next step

After endpoint validation/tests are in place, choose one of:

1. Prepare frontend integration/demo against the validated HTTP contract.
2. Add API-operational envelope fields later (request id / tracing / pagination).
