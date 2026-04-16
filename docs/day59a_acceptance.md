# Day 59A Acceptance

## Today objective
Refine the already-implemented Day 59 authoritative multi-court pipeline with a minimal-diff update:

- fix child crawler court-entry / pagination behavior,
- make `sentence_id` the authoritative duplicate identity,
- keep Day 59 pipeline order and metadata timing policy unchanged.

## What Day 59A changes vs Day 59
Day 59A is an **incremental refinement, not a redesign**.

It keeps:

- per-court crawl
- merge/dedupe authoritative corpus
- downstream prep/retrieval consumption
- metadata attachment post-merge (model-preferred, deterministic fallback)

It changes:

1. child crawler court-entry now requires homepage form submission to establish each court run snapshot;
2. pagination becomes page-only after snapshot establishment (no URL-level court rewriting authority);
3. authoritative dedupe identity is simplified to `sentence_id`;
4. records without usable `sentence_id` are skipped from default authoritative merged corpus;
5. page audit/report fields and child success/failure status are aligned with actual exit code.

## Why `sentence_id` is authoritative identity now
`sentence_id` is directly tied to judgment sentence detail identity (e.g. `/sentence/zh/{id}`, `/sentence/pt/{id}`), making it a more stable and auditable authoritative key than multi-key URL/metadata fallback mixtures.

## Why homepage form submission is required for court entry
Observed source behavior indicates court context must be established through real homepage form interaction. URL synthesis alone is no longer treated as authoritative court switching.

## Why URL/href pagination is allowed only after snapshot establishment
Once page 1 snapshot is established from homepage form search, pagination links or page-only URL derivation can safely navigate additional pages within that established result context.

## New duplicate policy (Day 59A)
- Primary/authoritative identity: `sentence_id`.
- Missing `sentence_id`: skipped by default in authoritative path.
- Duplicate `sentence_id`: skipped with explicit reason counter.
- Any legacy URL/fallback metadata duplicate logic is compatibility-only and not authoritative in Day 59A.

## New page retry/recovery policy
- Child crawler includes explicit result stability checks (card fingerprint stability).
- On page navigation timeout/error, retry at least once.
- Before retrying, re-establish court snapshot via homepage form submission.

## Explicit notes
- `court=all` remains useful for broad coverage/debug/demo, but is **not** authoritative full harvest.
- Records without usable `sentence_id` are **not part of default authoritative merged corpus** in this round.

## Acceptance checklist
- [ ] Child crawler has explicit `start_court_search_from_home(...)` helper.
- [ ] Child crawler has page-only URL helper (no court rewrite authority).
- [ ] Page 1 always established through homepage form submission.
- [ ] Stability helper exists (card-count/fingerprint style check).
- [ ] Retry/recovery is present for page navigation failure.
- [ ] Crawl-time sentence-id extraction + sentence-id-first dedupe is explicit.
- [ ] Missing sentence-id records are skipped from authoritative admission path.
- [ ] Child page-audit log includes court/page/url/cards/retry/status and sentence-id slices.
- [ ] Child summary includes required sentence-id counters.
- [ ] Child success/failure output matches process exit code.
- [ ] Parent merge dedupe is sentence-id-first.
- [ ] Parent logs per-court raw/with-sentence-id/missing/duplicate counters.
- [ ] Parent logs merged candidate total and merged authoritative total.
- [ ] Metadata attachment timing/policy remains post-merge and unchanged in principle.
- [ ] No frontend contract change.
- [ ] No LangChain/LlamaIndex/agent framework introduction.
- [ ] No large generated artifacts committed.

## Evidence developer must provide
- changed file list;
- example CLI commands;
- sample child page-audit log shape;
- sample merged manifest/report shape;
- concise Day 59A delta explanation;
- concise rationale for homepage-form court entry;
- concise rationale for sentence-id authoritative dedupe.
