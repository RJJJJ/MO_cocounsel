# Day 24 Acceptance

## Today objective

Add an all-court crawling mode on top of the existing stable Macau court append-to-corpus pipeline, with `court=all` as default while preserving single-court debug/regression modes.

## Deliverables

1. `crawler/pipeline/add_all_court_crawling_mode.py`
   - Playwright-based pipeline entrypoint;
   - supports `--court` CLI (`all`, `tsi`, `tui`, `tjb`, `ta`);
   - default page range `1..10`;
   - keeps existing stop conditions and duplicate handling based on corpus manifest;
   - appends new cases into existing corpus layout.

2. `crawler/pipeline/add_all_court_crawling_mode_spec.md`
   - rationale for coverage-first expansion;
   - all-court + single-court mode design;
   - duplicate handling and stop conditions;
   - next-step recommendation.

3. local runtime output (not committed as large artifact)
   - `data/corpus/raw/macau_court_cases/all_court_crawl_report.txt`.

## Acceptance checklist

- [ ] Default mode is `--court all`.
- [ ] Supports debug overrides: `tsi`, `tui`, `tjb`, `ta`.
- [ ] Uses stable flow: search -> select court -> submit -> parse cards -> follow detail -> body-first extract -> append corpus.
- [ ] Stops on invalid/no-result page.
- [ ] Stops on duplicate result page signature.
- [ ] Reuses manifest-based duplicate rules.
- [ ] Appends only new records into existing corpus layout.
- [ ] Does not break existing single-court path (kept in parallel as debug/regression mode).
- [ ] Does not modify README.
- [ ] Does not add vector retrieval or database work.
- [ ] No large generated artifacts committed in diff.

## Evidence developer must provide

1. command used to run crawler, e.g.:
   - `python crawler/pipeline/add_all_court_crawling_mode.py --court all`
2. terminal summary containing at least:
   - court mode used
   - pages attempted
   - valid pages parsed
   - cards discovered
   - detail pages attempted
   - detail pages succeeded
   - duplicates skipped
   - new corpus records added
   - whether all-court crawling appears successful
3. report file path confirmation:
   - `data/corpus/raw/macau_court_cases/all_court_crawl_report.txt`
4. `git status` evidence showing no large generated artifacts included in commit.
