# Day 20 Spec: Extend Pagination Range and Append Corpus

## Why coverage is now the main bottleneck
Day 17 to Day 19 already validated the full pipeline shape:
1. result-page discovery is stable,
2. selector-driven card parsing is stable,
3. detail TXT extraction is stable,
4. raw corpus layout is stable.

Because structure is proven, the limiting factor is dataset breadth. The next useful increment is to crawl deeper pagination and append only net-new cases into the existing raw corpus.

## Page range strategy
- Start from a real submitted result state:
  - open search page,
  - select `中級法院` (`court=tsi`),
  - submit search.
- Use the submitted result URL as baseline.
- Visit pages `1..10` by setting `page` query param.
- Parse each page only with the validated selector flow (`div#zh-language-case.case_list > li` cards).
- Stop early only if clear stop condition is met (see stop conditions section).

## Duplicate handling rules
Manifest source:
- `data/corpus/raw/macau_court_cases/manifest.jsonl`

Duplicate key priority (source-identity-first):
1. normalized `text_url_or_action`,
2. normalized `pdf_url` when text URL is missing,
3. fallback metadata key `(court, authoritative_case_number, authoritative_decision_date, language)` only when both URLs are missing.

`authoritative_case_number` and `authoritative_decision_date` continue to be sourced from list-page fields (`source_list_case_number`, `source_list_decision_date`) for fallback consistency.

If duplicate key already exists:
- skip corpus write,
- increment duplicate counter,
- log the skipped duplicate details (e.g. into `skipped_duplicates.txt`),
- keep crawl running.

## Append-to-corpus rules
For every new (non-duplicate) case:
- write `full_text.txt` under `data/corpus/raw/macau_court_cases/cases/<language>/<year>/<case_slug>/`
- write `metadata.json` next to `full_text.txt`
- append one JSON line to `manifest.jsonl`
- keep existing corpus content unchanged (append-only behavior)

Directory collision handling:
- if target folder already exists, add `__dupN` suffix for filesystem uniqueness.

## Stop conditions
Crawler may stop before page 10 only when one of these is true:
1. No valid cards found on current page.
2. Current page signature duplicates a prior page signature (pagination loop/repeat).

If neither condition occurs, crawler proceeds through page 10.

## Recommended next step
After this coverage extension, prioritize one of:
1. Build chunking-prep layer for downstream LLM retrieval,
2. Add multi-court crawling (`tui`, `tjb`, `ta`) using the same append + dedupe contract.
