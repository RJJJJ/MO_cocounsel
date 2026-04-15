# Day 7 Acceptance - Requests Replay Validation

## Today objective
Replay the real browser-captured Macau Courts search submit request using `requests` only, and verify whether session + token refreshed replay can return post-submit content without Playwright.

## Deliverables
1. `crawler/source_probes/court_requests_replay_probe.py`
2. `crawler/parsers/court_requests_replay_spec.md`
3. Probe artifacts under `data/raw/court_probe/`:
   - `requests_replay_after_submit.html`
   - `requests_replay_report.txt`

## Acceptance checklist
- [ ] Probe uses `requests` + `BeautifulSoup` only.
- [ ] Probe uses `requests.Session()`.
- [ ] Probe performs preflight GET on search page to refresh cookie/session/token state.
- [ ] Probe posts to `https://www.court.gov.mo/zh/subpage/researchjudgments?court=tui` (or resolved equivalent form action from preflight page).
- [ ] Payload includes required Day 6-captured field names:
  - [ ] `wizcasesearch_sentence_filter_type[court]`
  - [ ] `wizcasesearch_sentence_filter_type[decisionDate][left_date]`
  - [ ] `wizcasesearch_sentence_filter_type[decisionDate][right_date]`
  - [ ] `wizcasesearch_sentence_filter_type[recContent][logic]`
  - [ ] `wizcasesearch_sentence_filter_type[recContent][key][]`
  - [ ] `wizcasesearch_sentence_filter_type[_token]`
- [ ] Date range is recent 30 days.
- [ ] Request headers include `User-Agent`, `Referer`, and `Content-Type`.
- [ ] Probe saves required artifacts.
- [ ] Terminal output includes:
  - [ ] preflight GET status
  - [ ] POST status
  - [ ] final URL
  - [ ] response length
  - [ ] whether page still looks like search form
  - [ ] whether page contains candidate case markers
  - [ ] whether replay appears successful
- [ ] No DB integration.
- [ ] No Playwright usage.
- [ ] No full crawler implementation.

## Evidence developer must provide
- Command used to run Day 7 replay probe.
- Terminal output excerpt with all required summary fields.
- Paths to generated Day 7 artifacts.
- Short conclusion on whether requests replay appears validated now.
