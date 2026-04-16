# Day 55 Acceptance: Endpoint Validation and Tests

## Today objective

Strengthen and verify endpoint-level validation for `POST /api/research/query` so the HTTP contract is stable and regression-protected before frontend integration.

## Deliverables

- Added endpoint tests:
  - `tests/test_research_endpoint.py`
- Strengthened request validation:
  - reject blank/whitespace-only `query`
  - enforce `top_k >= 1` and correct type via schema validation
- Added Day 55 implementation spec:
  - `crawler/pipeline/endpoint_validation_and_tests_spec.md`

## Acceptance checklist

- [ ] Happy path test passes for `{"query":"假釋","top_k":5}` with `200` response.
- [ ] Response envelope keys asserted:
  - `schema_version`
  - `query`
  - `top_k`
  - `result_count`
  - `diagnostics`
  - `results`
- [ ] Diagnostics keys asserted:
  - `retrieved_cases_count`
  - `case_cards_built`
  - `model_generated_metadata_used_count`
  - `deterministic_fallback_used_count`
  - `success_flag`
- [ ] Missing `query` returns validation error (`422`).
- [ ] Invalid `top_k` values (`0`, negative, wrong type) return validation error (`422`).
- [ ] Empty/blank `query` returns validation error (`422`).
- [ ] No DB, no external API, no cloud model call in tests.
- [ ] No retrieval ranking or metadata generation behavior changes.

## Evidence developer must provide

1. `pytest tests/test_research_endpoint.py` output (pass/fail).
2. `git diff --stat` showing only intended code/docs changes.
3. Short summary mapping each checklist item to:
   - test name
   - file path
   - assertion coverage
