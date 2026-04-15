# Day 6 Acceptance - Playwright Verification Probe

## Today objective
Confirm whether the Macau Courts judgment search can reach real results only via browser interaction, and capture the real request flow needed for next-step implementation planning.

## Deliverables
1. `crawler/source_probes/court_playwright_probe.py`
2. `crawler/parsers/court_playwright_spec.md`
3. Probe artifacts under `data/raw/court_probe/`:
   - `playwright_before_submit.html`
   - `playwright_after_submit.html`
   - `playwright_after_submit.png`
   - `playwright_network_log.json`
   - `playwright_probe_report.txt`

## Acceptance checklist
- [ ] Probe uses Playwright for Python.
- [ ] Probe opens the target court judgment search page.
- [ ] Probe waits for interactive-ready state.
- [ ] Probe fills recent-30-day date fields (minimal required fields first).
- [ ] Probe clicks search button through browser interaction.
- [ ] Probe captures navigation events.
- [ ] Probe captures network request URL/method and POST data if present.
- [ ] Probe saves all required artifacts.
- [ ] Probe terminal output includes:
  - submit success status,
  - post-submit URL,
  - result-marker presence,
  - request count,
  - likely submission capture status,
  - replay feasibility assessment.
- [ ] No DB integration.
- [ ] No full crawler implementation.

## Evidence developer must provide
- Command used to run the probe.
- Terminal output excerpt showing required summary fields.
- Paths of generated artifacts.
- Short conclusion:
  - whether browser interaction appears required,
  - and whether next step should be requests replay or continued Playwright extraction.
