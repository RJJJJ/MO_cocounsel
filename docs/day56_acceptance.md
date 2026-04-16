# Day 56 Acceptance

## Today objective
Prepare a minimal but presentable frontend/demo integration for the validated FastAPI research endpoint (`POST /api/research/query`) without changing backend response contract or model/retrieval logic.

## Deliverables
1. `frontend/demo_research_integration.html`
   - Minimal interactive UI for `query` + `top_k` input.
   - Calls `POST /api/research/query`.
   - Renders `result_count`, `diagnostics`, and case-card focused fields including `metadata_source`, `pdf_url`, `text_url_or_action`.
2. `frontend/demo_research_integration_plan.md`
   - Demo flow.
   - Request/response mapping.
   - Displayed fields.
   - Current limitations.
   - Recommended next step.
3. `docs/day56_acceptance.md` (this file)
   - Objective, deliverables, acceptance checklist, and evidence requirements.

## Acceptance checklist
- [ ] Demo can send valid payload with `query` and `top_k`.
- [ ] Demo uses `POST /api/research/query` exactly.
- [ ] Demo displays `result_count` and diagnostics content.
- [ ] Demo displays case cards with source/link fields:
  - [ ] `metadata_source`
  - [ ] `pdf_url`
  - [ ] `text_url_or_action`
- [ ] No backend contract changes.
- [ ] No default model changes.
- [ ] No retrieval / metadata generation / promotion logic changes.
- [ ] No large generated artifacts committed.
- [ ] README unchanged.

## Evidence developer must provide
- Git diff summary showing only frontend/demo/docs scope changes.
- Command output for at least one relevant test/check run (e.g., endpoint tests) to confirm no regression in API contract.
- Optional runtime screenshot or manual run note demonstrating form submit and rendered sections.
