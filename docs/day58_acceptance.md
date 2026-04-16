# Day 58 Acceptance

## Today objective
Improve frontend case-card density/layout for the research demo so larger result sets are faster to scan and compare, without changing backend contract or retrieval/metadata/model logic.

## Deliverables
1. `frontend/demo_research_integration.html`
   - Refine case-card visual density and spacing hierarchy.
   - Keep all currently displayed fields available.
   - Implement progressive disclosure for long fields (`case_summary`, `holding`, `legal_basis`, `disputed_issues`) collapsed by default.
   - Add per-card expand/collapse control for long-field sections.
   - Keep existing filter/sort controls and query flow intact.
2. `frontend/demo_research_integration_plan.md`
   - Add Day 58 goals and updated compact-card behavior.
   - Document progressive disclosure behavior.
   - Capture post-Day-58 limitations.
   - Recommend next step (request id/tracing/pagination fields later, or a polished demo shell).
3. `docs/day58_acceptance.md` (this file)
   - Objective, deliverables, acceptance checklist, and required evidence.

## Acceptance checklist
- [ ] Demo still sends valid payload with `query` and `top_k` to `POST /api/research/query`.
- [ ] Card layout is denser and easier to scan (improved title/subtitle/metadata hierarchy).
- [ ] Basic metadata is shown in compact/two-column style (or equivalent compact presentation).
- [ ] Long fields are collapsed by default:
  - [ ] `case_summary`
  - [ ] `holding`
  - [ ] `legal_basis`
  - [ ] `disputed_issues`
- [ ] Per-card expand/collapse control works for long sections.
- [ ] Tag layout is cleaner and remains readable under many tags.
- [ ] No backend response contract changes.
- [ ] No retrieval / metadata generation / model logic changes.
- [ ] No large generated artifacts committed.
- [ ] README unchanged.

## Evidence developer must provide
- Git diff summary showing only frontend/docs scope changes.
- Command output for at least one relevant repository check.
- Manual verification note demonstrating:
  - query submission and successful response rendering,
  - compact metadata scan behavior,
  - long-field collapsed-by-default behavior,
  - per-card expand/collapse behavior,
  - filter/sort still working after layout changes.
