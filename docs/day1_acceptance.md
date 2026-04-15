# Day 1 Acceptance

## Today's Objective

Deliver a concrete, retrieval-first documentation baseline that converts project vision into executable week-1 engineering contracts.

---

## Deliverables Checklist

- [ ] README updated to keep original architecture/capability vision while clarifying MVP scope.
- [ ] README explicitly states: Macau judgments + Macau statutes are MVP-first targets.
- [ ] README explicitly states: architecture is cross-domain, not labor-law-limited.
- [ ] README explicitly states: Day 1 does not implement agent orchestration.
- [ ] `docs/mvp_contract.md` created.
- [ ] `docs/source_inventory.md` created with required source fields.
- [ ] `docs/domain_model.md` created with required entities and rationale.
- [ ] `docs/day1_acceptance.md` created.

---

## Acceptance Checklist

A reviewer should accept Day 1 if all conditions below are true:

1. Core principle remains intact: **Macau Legal Retrieval Engine first, agents second**.
2. README no longer implies product scope is labor law only.
3. MVP contract is implementation-oriented (Day 1–7), not conceptual only.
4. Source inventory includes official-source feasibility and risk fields.
5. Domain model can directly support ingestion, retrieval, and citation grounding.
6. Out-of-scope section clearly blocks premature orchestration work.

---

## Evidence the Developer Should Provide After Completion

1. `git diff` showing only README and docs changes (no runtime feature code).
2. A short summary mapping each requirement to the exact file and section.
3. Confirmation that all new docs are English and style-consistent.
4. If any required source detail is still uncertain, list explicit Day 2 validation tasks.
5. Final commit hash containing the Day 1 documentation package.
