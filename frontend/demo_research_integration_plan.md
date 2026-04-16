# Day 57 Frontend Demo Research Integration Plan

## Demo flow
1. Developer opens `frontend/demo_research_integration.html` in a browser while FastAPI service is running.
2. User inputs:
   - `query` (string)
   - `top_k` (integer, min 1)
3. Frontend sends `POST /api/research/query` with JSON payload.
4. On success, UI renders:
   - envelope summary (schema version, query, top_k, result_count)
   - diagnostics block (collapse/expand)
   - case controls (filter + sort)
   - case cards list (based on current controls)
5. On failure, UI shows error status with HTTP code and response body snippet.
6. User can refine current result set client-side without re-calling API:
   - filter by `metadata_source`
   - filter by `language`
   - sort by `authoritative_decision_date` or `authoritative_case_number`
   - choose ascending/descending order

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

## Supported controls
- Filter controls:
  - `metadata_source` (All + values discovered from current response)
  - `language` (All + values discovered from current response)
- Sort controls:
  - `authoritative_decision_date`
  - `authoritative_case_number`
  - `sort_order` toggle: ascending / descending
- Diagnostics visibility:
  - native collapse/expand behavior via `<details>` in diagnostics panel

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
- Error display is plain-text status only.
- Assumes same-origin API path for `/api/research/query`.
- Filtering/sorting is in-memory for current response only (no URL-state shareability).
- Sort semantics are string/date heuristic based; no server-side collation guarantees.

## Recommended next step
- Add transport observability fields in future contract extension (e.g., request id / tracing / pagination fields) once backend roadmap allows.
- Improve case-card density/layout for demo review at larger result counts (e.g., compact rows, two-column metrics, and progressive disclosure).
