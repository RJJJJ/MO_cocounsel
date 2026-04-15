# Court Requests Replay Spec (Day 7)

## Replay target endpoint
- Primary replay target:
  - `https://www.court.gov.mo/zh/subpage/researchjudgments?court=tui`
- Strategy:
  1. Preflight `GET` on the same endpoint to refresh server-side session + cookie state.
  2. Resolve form `action` from preflight HTML (if present) for the replay `POST` target.
  3. Fallback to the same URL if no form action is found.

## Fields replayed (from Day 6 captured request shape)
The replay payload includes these real form namespaces:
- `wizcasesearch_sentence_filter_type[court]`
- `wizcasesearch_sentence_filter_type[decisionDate][left_date]`
- `wizcasesearch_sentence_filter_type[decisionDate][right_date]`
- `wizcasesearch_sentence_filter_type[recContent][logic]`
- `wizcasesearch_sentence_filter_type[recContent][key][]`
- `wizcasesearch_sentence_filter_type[_token]`

Date window is set to recent 30 days.

## Session handling strategy
- Use `requests.Session()` for both requests.
- Keep cookies from preflight `GET` and automatically reuse them in `POST`.
- Send browser-like `User-Agent` for both requests.
- Send `Referer` and `Content-Type: application/x-www-form-urlencoded` for `POST`.

## Token refresh strategy
- Parse the preflight HTML with BeautifulSoup.
- Prefer exact input name `wizcasesearch_sentence_filter_type[_token]`.
- Fallback to any hidden input whose field name contains `_token`.
- Abort replay if token is missing (avoid stale or guessed token submissions).

## Replay result interpretation
Probe records:
- preflight GET status
- POST status
- final URL
- response length
- whether HTML still looks like a search form
- whether HTML contains candidate case markers
- combined success heuristic (`replay_appears_successful`)

Heuristic definition in this probe:
- `POST == 200`
- candidate-case markers detected
- page does **not** strongly look like search-form fallback

## Whether requests replay is now validated
- Validation status is determined by `requests_replay_report.txt` generated from an actual run.
- If `replay_appears_successful: True`, Day 7 replay is validated for next-stage parsing experiments.
- If False, request replay shape exists but still needs field/value refinement or follow-up flow discovery.

## Recommended next step
- If validated: implement a narrow result-list extractor over replay HTML and verify stable row/card parsing.
- If not validated: compare Day 6 captured payload values one-by-one (including optional hidden fields) and retry with tighter field parity.
