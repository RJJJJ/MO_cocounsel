# Day 16A — Paginated Result Card Boundary Fix Spec

## What was wrong in Day 15 output

Day 15 successfully preserved `pdf_url` and `text_url_or_action`, but extraction still had boundary errors:

- One extracted record sometimes contained text from multiple judgment cards.
- `case_number` regressed to truncated fragments (e.g., `26/03`).
- `case_type` regressed to invalid residue (e.g., `/2026`).
- `subject`, `summary`, and `assistant_judges` were contaminated by neighboring cards.

This indicates the bottleneck moved from pagination/link capture to card-container segmentation quality.

## Why link preservation was not enough

Even perfect link capture cannot fix field corruption when record boundaries are wrong.

- If a DOM block spans multiple cards, regex extraction will blend labels/values across cards.
- Case header parsing from blended text is unstable and can produce partial `case_number` or invalid `case_type`.
- Field-level quality depends on isolating one stable card container before any parsing logic.

## Card-boundary segmentation strategy

The Day 16A extractor uses **DOM-first segmentation** (not raw full-block regex only):

1. Collect repeated structural nodes (`div/li/article/section/tr`) and compute signature frequency (`tag|class`).
2. Keep candidate nodes only if:
   - repeated signature count is high enough (stable repeated list/card pattern), and
   - textual score indicates card semantics (case/date/subject/summary/result hints).
3. Build candidate hierarchy and prefer **atomic leaf candidates** (containers that do not include other candidate containers), to avoid parent wrappers that merge multiple cards.
4. Parse each selected container independently into exactly one output record.

## Field-isolation strategy

Each selected card container is parsed in isolation:

- Case header extraction uses per-card line list (`innerText` line split), then case-number + case-type parsing from the same line neighborhood.
- Label fields (`subject`, `summary`, `decision_result`, `reporting_judge`, `assistant_judges`) are read from card-local lines only.
- Link parsing scans card-local interactive nodes (`a/button/span/i/role=button`) and preserves:
  - `pdf_url`
  - `text_url_or_action`
  - `text_link_language` (`zh`/`pt` when sentence path is detected).

## Contamination detection rules

A record is flagged as suspicious if one of these holds:

- more than one case-number hit in `raw_card_text`, or
- more than one decision-date hit in `raw_card_text`, or
- excessive repeated label occurrences (`主題/摘要/裁判結果`) implying multi-card blending.

These counts are included in terminal/report metrics.

## Success criteria

Boundary fix appears successful when:

- parsed records are one-card-per-record (low/no contamination flags),
- `case_number` matches normalized shape like `36/2026`, `126/2026`, `253/2026`,
- `case_type` is non-empty and not malformed residual like `/2026`,
- `subject`/`summary` remain card-local,
- link fields remain preserved (`pdf_url`, `text_url_or_action`).

## Recommended next step

1. Primary: run batch text-detail extraction from these cleaned paginated cards.
2. Optional hardening: inspect additional page-layout variants (court/language/date-range permutations) and add variant-specific card-container selectors if needed.
