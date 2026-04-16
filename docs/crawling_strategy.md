# Crawling Strategy Notes

This document records crawling strategy decisions for Macau court source acquisition.

## Court coverage strategy

The `court=all` mode should be treated as a useful discovery and validation mode, but it should not automatically be assumed to be the final full-ingestion path.

### Why

Observed behavior suggests that `court=all` may behave like a fixed search window or aggregated result view rather than a truly exhaustive cross-court export surface.

It can still be useful for:

- early pipeline validation
- selector testing
- pagination checks
- quick coverage sampling

But it may be unreliable as the only long-run source for complete corpus acquisition.

Additional observation: when using `court=all`, result windows may repeat across pages, which can inflate apparent coverage without increasing unique judgments.

## Day 59 authoritative full-corpus assembly stance

Day 59 establishes a concrete, auditable authoritative flow:

1. Crawl each court independently (`tui`, `tsi`, `tjb`, `ta`).
2. Collect each court-run manifest as explicit source input.
3. Merge all court outputs into one candidate pool.
4. Deduplicate **after merge** with auditable reason breakdown.
5. Preserve provenance fields for every merged record.
6. Publish merged corpus manifest/report as the authoritative downstream source.

## Per-court harvest rationale

Per-court runs improve control over:

- recall tracking by court
- reproducibility/debuggability of crawl windows
- source-specific diagnostics
- explicit merge/dedupe accountability

This is safer than inferring completeness from a single aggregated query mode.

## Merge/dedupe rationale (refined in Day 59A)

Deduplication belongs at merged-corpus assembly time so cross-court duplicates are visible and auditable in one place.

Day 59A refines authoritative identity to **sentence-id-first**:

- authoritative duplicate key: `sentence_id` extracted from sentence detail URLs;
- missing sentence id: skipped by default in authoritative merged corpus;
- duplicate reason counters centered on:
  - `duplicate_sentence_id`
  - `missing_sentence_id_skipped`
- legacy URL/metadata identity logic remains compatibility-only, not primary authority.

## Day 59A child court-entry and pagination refinement

Old child behavior mixed:

- homepage form entry,
- URL-level court param rewriting,
- URL-driven page navigation.

Day 59A now requires:

1. establish page-1 result snapshot by homepage form submission per court;
2. only then allow pagination via href or page-only URL derivation;
3. do not treat URL court rewriting as authoritative court switching.

This improves court-context correctness and reduces court-switch ambiguity.

## Metadata attachment stage rationale

Metadata is no longer treated as per-crawl default behavior. The authoritative sequence is:

- build authoritative merged corpus first
- let retrieval/prep consume that corpus
- attach metadata after merge with source preference:
  - prefer model-generated metadata when available
  - deterministic baseline fallback otherwise

Deterministic baseline remains required as fallback + benchmark/regression guard.

## Recommended operating stance

- Keep `court=all` available as a fast path and comparison mode.
- Do not assume `court=all` equals full recall.
- Validate coverage by comparing `court=all` against per-court runs.
- Prefer per-court crawling + merge/dedupe when completeness matters.

## Current limitations after Day 59

- Coverage quality still depends on page-window configuration (no automatic completeness proof).
- Merge policy currently keeps first-seen records by duplicate key priority.
- Metadata attachment remains case-level source preference; no per-field blending policy yet.
- Retrieval/eval regression pack for the new authoritative corpus is not yet bundled.
- Child crawler still depends on upstream site stability and selector continuity.
- Completeness proof remains bounded by configured page windows.

## Day 60 convergence-crawl rationale

Single-pass page scans are now explicitly treated as potentially incomplete because page drift can move records across pages/runs. Day 60 extends the authoritative strategy to **per-court repeated rescans**:

1. converge court A (e.g., `tui`) by repeated full-pass rounds;
2. then converge court B (`tsi`);
3. then court C (`tjb`);
4. then court D (`ta`);
5. then merge/dedupe.

Convergence stop is operationally defined as:

- configured consecutive rounds with zero newly discovered `sentence_id`.

This improves practical coverage but does not claim mathematical exhaustiveness.

## Current limitations after Day 60

- Convergence criteria are heuristic and configurable, not a completeness proof.
- Some discovered `sentence_id` may still fail detail extraction due to transient site issues.
- Round/page retries are conservative; severe site instability can still reduce coverage.
- Metadata remains post-merge attachment; Day 60 does not regenerate metadata.
- Retrieval regression baselines for convergence effects are not yet bundled.

## Day 61 recommended next step

Build a **convergence results audit + retrieval regression pack** against the sentence-id-authoritative merged corpus, including coverage delta tracking by court and duplicate-policy regression checks.

### Engineering note

This remains primarily a source-acquisition and coverage-control decision, not just a parser detail. Ingestion authority should be driven by recall, reproducibility, provenance, and duplicate control.
