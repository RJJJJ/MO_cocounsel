# Day 13 Playwright text-detail batch extraction spec

## Why Day 12 should be treated as functionally successful

Day 12 already recovered 3 non-empty text-detail samples and recorded 0 extraction failures for those samples. This satisfies the core goal of proving TXT/fulltext detail extraction can work on resolved sentence URLs. The previous failure conclusion was caused by an overly strict success flag tied to `direct_sentence_pages_opened_count` instead of validated text output.

## Corrected success heuristic (Day 12 and Day 13)

Extraction run should be considered successful when all of the following hold:

1. `successful extractions > 0`
2. `non-empty full_text count > 0`
3. failure ratio is acceptable (default <= 50%)

Important correction:

- `direct_sentence_pages_opened_count == 0` **must not** automatically mean overall failure.
- navigation counters are diagnostic only; validated full-text recovery is the primary success signal.

## Controlled batch extraction strategy

1. Read `data/parsed/court_probe/playwright_result_cards_refined.json`.
2. Filter records where `text_url_or_action` is a resolved sentence URL (`/sentence/zh/<id>` or `/sentence/pt/<id>`).
3. Select a controlled prefix batch with target range 20–50.
   - If fewer than 20 are available in current input scope, process all available resolved URLs and report this explicitly.
4. For each selected URL:
   - Primary path: direct `page.goto(url)` and extract visible judgment text.
   - Fallback path (secondary): retry with modal/overlay/body extraction.
5. Keep records only when `full_text` passes quality validation.
6. Write detail corpus to JSONL:
   - `data/parsed/court_probe/playwright_text_details_batch.jsonl`
7. Write summary report:
   - `data/parsed/court_probe/playwright_text_details_batch_report.txt`

## Language distribution handling

Use URL-based rules:

- URL contains `/zh/` -> `language = zh`
- URL contains `/pt/` -> `language = pt`
- otherwise -> `language = unknown`

Report metrics must include `zh count` and `pt count`.

## Text quality validation rules

A detail page is valid only if:

- `full_text` is non-empty after cleanup
- length >= 240 characters
- token count >= 60 words/tokens
- not metadata-only (e.g., case number + date + short stub)

Metadata-only guard:

- if both case number pattern and date pattern exist but total length is too short, reject.

## Remaining risks

- Current scope depends on single refined result-card file; if resolved URLs are fewer than 20, batch size is input-limited.
- Some legacy sentence pages may render content with alternate HTML templates, which can reduce extraction coverage.
- Anti-bot / intermittent load latency may affect a subset of URLs; fallback helps but cannot eliminate all transient failures.

## Recommended next step

Pick one of:

1. Add pagination to expand resolved URL pool before batch extraction.
2. Build a raw corpus storage layout (partition by language/date/case_number) for downstream indexing and QA.
