# Day 24 Spec: Add All-Court Crawling Mode

## Why coverage expansion is now more valuable than architecture expansion

At Day 23, the selector-driven parsing, detail extraction, pagination extension, corpus append pipeline, and local BM25 prototype are already stable enough for iterative use. The current bottleneck is not crawler architecture, but recall coverage:

- single-court crawl limits corpus growth and query recall;
- search endpoint now supports `court=all`, enabling one-pass broader recall;
- expanding source coverage now yields more practical retrieval gains than adding another architecture layer.

Therefore, Day 24 prioritizes **coverage expansion** by promoting all-court crawling to the default mode while preserving existing stable pipeline behavior.

## All-court mode design

New pipeline entrypoint:

- `crawler/pipeline/add_all_court_crawling_mode.py`

Core flow (unchanged in architecture, expanded in court scope):

1. open Macau court search page;
2. select court in the search form (`court=all` by default);
3. submit search;
4. parse result cards with selector-driven extraction;
5. follow `text_url_or_action` links;
6. perform body-first detail extraction and text cleaning;
7. append non-duplicate records into the existing raw corpus layout.

CLI:

- `--court all` (default, production coverage mode)
- `--court tsi`
- `--court tui`
- `--court tjb`
- `--court ta`

Pagination defaults to page range `1..10`, with configurable `--start-page` and `--end-page`.

## Single-court debug mode design

Single-court modes are preserved as regression and debugging paths:

- useful for controlled runs when parsing or detail extraction issues occur;
- useful for comparing behavior with historical single-court baselines;
- avoids breaking existing known-good narrow-scope workflows.

These modes reuse the same parser/extractor/append logic, differing only in `court` filter.

## Duplicate handling

Duplicate handling now prioritizes source-document identity to avoid false deduplication across court levels:

- read `data/corpus/raw/macau_court_cases/manifest.jsonl`;
- build duplicate key using strict priority:
  1. normalized `text_url_or_action` (primary),
  2. normalized `pdf_url` (secondary, only if text URL missing),
  3. fallback metadata key `(court, authoritative_case_number, authoritative_decision_date, language)` only if both URLs are missing.
- skip only when the highest-priority available key already exists;
- append all non-duplicates to preserve distinct judgments that share case metadata but have different source URLs;
- keep existing corpus directory structure and manifest schema intact.

## Stop conditions

Validated stop conditions are retained:

1. **invalid/no-result page**: stop when parsed cards are empty;
2. **duplicate result page signature**: stop when a page repeats a previously seen card signature;
3. **configured page range reached**: stop after the configured end page.

## Local outputs (not committed)

Runtime writes local report:

- `data/corpus/raw/macau_court_cases/all_court_crawl_report.txt`

Report and console summary include:

- court mode used
- pages attempted
- valid pages parsed
- cards discovered
- detail pages attempted
- detail pages succeeded
- duplicate strategy used (`text_url_or_action -> pdf_url -> fallback metadata`)
- duplicates skipped
- duplicates skipped by `text_url`
- duplicates skipped by `pdf_url`
- duplicates skipped by fallback metadata key
- new corpus records added
- whether all-court crawling appears successful

## Recommended next step

Choose one next increment:

1. build a **hybrid retrieval layer skeleton** (BM25 + future semantic hook points), or
2. add an **evaluation/query test set** for recall/precision tracking and regression checks.
