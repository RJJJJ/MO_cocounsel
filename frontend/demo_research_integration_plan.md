# Day 56 Frontend Demo Research Integration Plan

## Demo flow
1. Developer opens `frontend/demo_research_integration.html` in a browser while FastAPI service is running.
2. User inputs:
   - `query` (string)
   - `top_k` (integer, min 1)
3. Frontend sends `POST /api/research/query` with JSON payload.
4. On success, UI renders:
   - envelope summary (schema version, query, top_k, result_count)
   - diagnostics block
   - case cards list
5. On failure, UI shows error status with HTTP code and response body snippet.

## Request/response mapping

### Request mapping (frontend -> API)
- `query` input -> `payload.query`
- `top_k` input (number) -> `payload.top_k`

```json
{
  "query": "假釋",
  "top_k": 5
}
```

### Response mapping (API -> frontend)
- `schema_version` -> summary metric
- `query` -> summary metric
- `top_k` -> summary metric
- `result_count` -> summary metric
- `diagnostics` -> pretty JSON diagnostics panel
- `results[]` -> case card collection

## Displayed fields
Each case card currently renders:
- `card_title`
- `card_subtitle`
- `authoritative_case_number`
- `authoritative_decision_date`
- `court`
- `case_type`
- `language`
- `metadata_source`
- `case_summary`
- `holding`
- `legal_basis`
- `disputed_issues`
- `card_tags`
- `pdf_url`
- `text_url_or_action`

## Current limitations
- Static HTML + inline JavaScript only (no production app shell).
- No persisted query history.
- No pagination or infinite scrolling.
- No client-side sorting/filtering controls.
- Error display is plain-text status only.
- Assumes same-origin API path for `/api/research/query`.

## Recommended next step
- Add transport observability fields in future contract extension (e.g., request id / tracing / pagination fields) once backend roadmap allows.
- Refine frontend UX with filtering/sorting controls for case cards and diagnostics visibility toggles.
