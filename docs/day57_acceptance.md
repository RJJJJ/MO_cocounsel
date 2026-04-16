# Day 57 Acceptance

## Today objective
Refine the frontend demo UX for `POST /api/research/query` exploration by adding client-side filtering/sorting controls and diagnostics visibility toggling, while keeping backend contract and retrieval/model logic unchanged.

## Deliverables
1. `frontend/demo_research_integration.html`
   - Add filter controls for:
     - `metadata_source`
     - `language`
   - Add sort controls for:
     - `authoritative_decision_date`
     - `authoritative_case_number`
     - ascending/descending order
   - Make diagnostics panel collapse/expand capable.
   - Preserve the existing query -> API -> render flow.
2. `frontend/demo_research_integration_plan.md`
   - Document Day 57 filtering/sorting UX flow.
   - List supported controls.
   - Capture current limitations after Day 57.
   - Recommend next step (request id/tracing/pagination fields later, and/or case-card density/layout improvements).
3. `docs/day57_acceptance.md` (this file)
   - Objective, deliverables, acceptance checklist, and evidence requirements.

## Acceptance checklist
- [ ] Demo still sends valid payload with `query` and `top_k` to `POST /api/research/query`.
- [ ] Diagnostics section supports collapse/expand.
- [ ] Filter controls are present and functional:
  - [ ] `metadata_source`
  - [ ] `language`
- [ ] Sort controls are present and functional:
  - [ ] `authoritative_decision_date`
  - [ ] `authoritative_case_number`
  - [ ] ascending/descending
- [ ] Case cards update based on active filter/sort controls.
- [ ] No backend contract changes.
- [ ] No retrieval / metadata generation / model logic changes.
- [ ] No large generated artifacts committed.
- [ ] README unchanged.

## Evidence developer must provide
- Git diff summary showing only frontend/demo/docs scope updates.
- Command output for at least one relevant repository check.
- Manual verification note that demonstrates:
  - query submission,
  - diagnostics collapse/expand,
  - filtering behavior,
  - sorting behavior.
