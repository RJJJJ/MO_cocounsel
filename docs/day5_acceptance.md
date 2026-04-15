# Day 5 Acceptance - Court Payload Matrix Probe

## Today objective
Refine POST payload construction for Macau Courts judgment search and compare multiple payload variants to identify combinations that are closer to a real result page (instead of search-form fallback).

## Deliverables
- `crawler/source_probes/court_payload_matrix_probe.py`
  - Uses `requests` + `BeautifulSoup` only.
  - Reads existing Day 3 form field artifact.
  - Tests payload matrix variants against one endpoint.
  - Supports at least two date formats for last-30-day range.
  - Saves per-variant response HTML and JSON summary under:
    - `data/raw/court_probe/payload_matrix/`
  - Prints probe conclusion in terminal.
- `crawler/parsers/court_payload_matrix_spec.md`
  - Documents endpoint, variants, date formats, criteria, best payload interpretation, unknowns, and recommendation.
- `docs/day5_acceptance.md`
  - Defines objective, checklist, and evidence requirements.

## Acceptance checklist
- [ ] No Playwright usage.
- [ ] No database interaction.
- [ ] No full crawler implementation.
- [ ] Probe reads existing form field metadata (`form_fields.json`).
- [ ] At least 4 payload variants tested.
- [ ] Date range is most recent 30 days.
- [ ] At least two date formats tested.
- [ ] Per-variant artifacts include:
  - [ ] response HTML
  - [ ] response summary with required fields
- [ ] Terminal output includes:
  - [ ] total payload variants tested
  - [ ] best candidate payload
  - [ ] whether any variant reduced form-page markers
  - [ ] recommendation: stay with requests or escalate

## Evidence developer must provide
- Command used to run Day 5 probe.
- Console output lines containing all required summary items.
- Path to aggregate report:
  - `data/raw/court_probe/payload_matrix/payload_matrix_report.json`
- Example per-variant artifact paths (at least 2 variants):
  - `data/raw/court_probe/payload_matrix/<variant>.html`
  - `data/raw/court_probe/payload_matrix/<variant>_summary.json`
