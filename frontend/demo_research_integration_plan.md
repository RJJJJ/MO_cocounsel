# Day 58 Frontend Demo Research Integration Plan

## Day 58 layout refinement goals
- Improve case-card scan efficiency for larger result sets without changing API contract.
- Keep all previously displayed fields visible in the UI, while reducing visual noise.
- Introduce progressive disclosure for long text fields so users can compare many cards quickly.

## Demo flow
1. Developer opens `frontend/demo_research_integration.html` in a browser while FastAPI service is running.
2. User inputs:
   - `query` (string)
   - `top_k` (integer, min 1)
3. Frontend sends `POST /api/research/query` with unchanged JSON payload.
4. On success, UI renders:
   - envelope summary (schema version, query, top_k, result_count)
   - diagnostics block (collapse/expand)
   - case controls (filter + sort)
   - compact case cards with dense metadata layout and per-card detail toggles
5. On failure, UI shows error status with HTTP code and response body snippet.
6. User can refine current result set client-side without re-calling API:
   - filter by `metadata_source`
   - filter by `language`
   - sort by `authoritative_decision_date` or `authoritative_case_number`
   - choose ascending/descending order

## Compact-card behavior
- Card header has tighter spacing hierarchy:
  - title (primary)
  - subtitle (secondary muted line)
  - per-card expand/collapse control for long sections
- Core metadata renders in a compact two-column grid:
  - `authoritative_case_number`
  - `authoritative_decision_date`
  - `court`
  - `case_type`
  - `language`
  - `metadata_source`
- Tag chips are grouped in a wrapped flex row with consistent spacing.
- Link row (`pdf_url`, `text_url_or_action`) remains visible near card footer.

## Progressive disclosure behavior
- Long fields are collapsed by default using `<details>` blocks with preview snippets:
  - `case_summary`
  - `holding`
  - `legal_basis`
  - `disputed_issues`
- Each card includes an `Expand details` / `Collapse details` button:
  - expands or collapses all long-field sections for that card at once
  - preserves independent behavior per card
- Preview text supports fast comparison across many cards before expanding.

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
- `results[]` -> compact case card collection

## Current limitations after Day 58
- Static HTML + inline JavaScript only (no production app shell).
- No persisted query history.
- No pagination or infinite scrolling.
- Error display is plain-text status only.
- Assumes same-origin API path for `/api/research/query`.
- Filtering/sorting is in-memory for current response only (no URL-state shareability).
- Per-card expansion state is not persisted between re-renders.

## Recommended next step
- Add request id / tracing / pagination fields in a future contract extension when backend roadmap permits.
- Or prepare a more polished demo shell (state persistence, responsive navigation, and reusable card components) for broader stakeholder review.
