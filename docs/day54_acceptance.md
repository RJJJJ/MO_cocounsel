# Day 54 Acceptance

## Today objective

Prepare a minimal FastAPI backend integration surface that exposes the existing API-ready research response envelope, while keeping retrieval and metadata logic unchanged.

## Deliverables

- `app/schemas/research.py`
- `app/api/research.py`
- `crawler/pipeline/fastapi_integration_surface_spec.md`
- `docs/day54_acceptance.md`

## Acceptance checklist

- [ ] New request schema includes:
  - `query: string`
  - `top_k: integer`
- [ ] New response schema includes:
  - `schema_version`
  - `query`
  - `top_k`
  - `result_count`
  - `diagnostics`
  - `results`
- [ ] `POST /api/research/query` is implemented.
- [ ] Endpoint calls existing Day 52 API-ready response envelope builder.
- [ ] Response keeps metadata artifact selection diagnostics visible (`selected_model_metadata_path`, `selected_model_metadata_case_count`).
- [ ] No retrieval logic changes.
- [ ] No metadata generation/selection logic changes.
- [ ] No DB integration, external API integration, or cloud model integration.
- [ ] No large generated artifacts committed.

## Evidence developer must provide

1. Command(s) run to sanity-check Python files (for example: compile/import checks).
2. Terminal output evidence that new FastAPI modules import successfully.
3. Git diff evidence showing only code/docs changes requested in Day 54.
