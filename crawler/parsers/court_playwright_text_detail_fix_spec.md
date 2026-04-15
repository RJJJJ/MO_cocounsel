# Day 12 Spec: TXT/fulltext detail extraction fix (direct sentence URL first)

## Why Day 11 detail extraction returned zero (or unstable)
- Day 11 detail extraction still treated popup/modal click paths as a first-class route.
- On current Macau court pages, refined `text_url_or_action` already resolves to direct sentence URLs (e.g. `/sentence/zh/42353`, `/sentence/pt/42361`).
- If extraction waits for popup behavior that does not reliably occur, content extraction can fail even though the URL itself is valid.

## Why direct sentence URL navigation is now the primary strategy
- Refined cards now include copyable, valid text sentence URLs.
- These URLs are the most stable machine path for predictable extraction.
- Direct `page.goto(text_url_or_action)` avoids dependency on frontend click wiring and modal timing.
- Popup/modal/overlay handling is demoted to fallback only when direct navigation clearly fails.

## zh / pt language handling rules
- URL path contains `/zh/` → `language = "zh"`.
- URL path contains `/pt/` → `language = "pt"`.
- Otherwise → `language = "unknown"`.

## Sentence-page extraction strategy
1. Read `data/parsed/court_probe/playwright_result_cards_refined.json`.
2. Select first 1–3 cards with usable `text_url_or_action` sentence URL.
3. Navigate directly with Playwright `goto`.
4. Extract visible text from likely main-content containers first.
5. Light cleanup: collapse whitespace, drop obvious UI strings (e.g. print/back labels).
6. Validate text is substantive (not metadata-only).
7. If direct content fails quality checks, run fallback overlay/modal extraction.

## Stable signals for identifying main text
- Main text block is long and structurally paragraph-like.
- Text body materially exceeds short metadata-only fragments.
- Presence of legal reasoning paragraphs is preferred signal.
- UI labels (e.g. print button text) are treated as noise and removed.

## Minimum success criteria
- At least one direct sentence page is opened.
- At least one non-empty `full_text` passes substantive thresholds.
- Each extracted sample records `language` correctly from URL.
- Output files are generated:
  - `data/parsed/court_probe/playwright_text_details_sample.json`
  - `data/parsed/court_probe/playwright_text_details_fix_report.txt`

## Recommended next step
- Either:
  1. move to controlled batch text-detail extraction using the same direct-URL strategy, or
  2. inspect additional detail-page variants (different courts/languages/layouts) and tune main-text selectors.
