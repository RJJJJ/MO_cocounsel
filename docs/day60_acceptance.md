# Day 60 Acceptance (Per-Court Convergence Crawling)

## Today objective
Implement a stable per-court convergence crawl strategy so each court is repeatedly rescanned until the crawler stops discovering new `sentence_id`, then moves to the next court.

## Why Day 60 matters
Day 59/59A established per-court authoritative harvesting + sentence_id-first identity + homepage-form entry. Day 60 addresses the remaining practical gap: **page drift can hide records in a single pass**.

## What problem Day 60 solves
A one-pass `page 1..N` crawl can miss sentence-id-backed records because result cards drift across pages/runs. Day 60 reframes this as a coverage problem and adds repeated rescans.

## New per-court convergence harvesting flow
1. Start from homepage search form.
2. Select one court.
3. Submit form and establish a fresh snapshot.
4. Scan pages forward.
5. Extract card `sentence_id`.
6. New `sentence_id` => attempt detail fetch.
7. Seen `sentence_id` => skip detail fetch immediately.
8. Repeat rounds until convergence.
9. Move to next court only after current court converges.

## Why page drift requires repeated rescans
Because card ordering/placement can change between runs, a single scan is not authoritative enough for practical full harvest. Repeated court rescans increase chance of discovering shifted records.

## Why sentence_id remains authoritative
- `sentence_id` is stable enough for cross-page/run identity.
- Day 60 keeps sentence_id-first logic for both child and parent authoritative paths.
- In this round, only sentence-id-backed records are part of the default authoritative corpus path.

## Convergence stop rules
- Default convergence stop: **2 consecutive rounds** with **0 new `sentence_id`**.
- Safety cap: configurable `--max-rounds`.
- Per-round page stop signals include:
  - no-result page
  - repeated page signature
  - configured page limits
  - optional consecutive pages with no new sentence_id

> Note: convergence means *operational stop criteria reached*, not proof of mathematical completeness.

## Deliverables
- Child crawler convergence mode + CLI flags + round/page audit outputs.
- Parent orchestration pass-through flags and court-by-court convergence reporting.
- Day 60 authoritative logic documented in code/docs.

## Acceptance checklist
- [ ] Child supports single-pass and convergence mode.
- [ ] Child convergence run loops by court rounds from homepage submission.
- [ ] Zero-new-round counting is based on newly discovered `sentence_id`.
- [ ] New sentence_id triggers detail fetch attempt.
- [ ] Seen sentence_id skips detail fetch.
- [ ] Detail fetch failure keeps sentence discovery and logs failure.
- [ ] Round-level stats and court-level convergence summary are emitted.
- [ ] Parent runs court-by-court convergence, then merge.
- [ ] Parent logs per-court convergence summary.
- [ ] `court=all` remains useful for broad coverage/debug/demo, not authoritative full harvest.
- [ ] Day 60 claims improved practical coverage, not perfect mathematical completeness.

## Evidence developer must provide
- Changed file list.
- Example CLI commands.
- Sample round audit output shape.
- Sample per-court convergence summary shape.
- Sample parent merged report shape.
- Concise Day 60 vs Day 59A delta.
- Concise convergence stopping logic explanation.
- Concise rationale for court-by-court convergence preference.
