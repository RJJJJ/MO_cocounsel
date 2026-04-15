# Crawling Strategy Notes

This document records crawling strategy decisions for Macau court source acquisition.

## Court coverage strategy

The court=all mode should be treated as a useful discovery and validation mode, but it should not automatically be assumed to be the final full-ingestion path.

### Why

Observed behavior suggests that court=all may behave like a fixed search window or aggregated result view rather than a truly exhaustive cross-court export surface.

It can still be useful for:

- early pipeline validation
- selector testing
- pagination checks
- quick coverage sampling

But it may be unreliable as the only long-run source for complete corpus acquisition.

### Practical implication

If the project later needs stronger global coverage, the safer default strategy is:

1. Crawl per-court result sets separately.
2. Preserve court-specific source metadata.
3. Merge outputs into one normalized corpus.
4. Deduplicate at corpus-build time.

### Recommended operating stance

- Keep court=all available as a fast path and comparison mode.
- Do not assume court=all equals full recall.
- Validate coverage by comparing court=all against per-court runs.
- Prefer per-court crawling plus merge when completeness matters more than convenience.

### Engineering note

This is mainly a source-acquisition and coverage-control decision, not just a parser detail. Even if court=all appears to work for some pages, ingestion design should still be driven by recall, reproducibility, and duplicate control.
