# Day 6 Playwright Verification Spec (Macau Courts Judgment Search)

## Probe purpose
Verify whether the Macau Courts judgment search page requires real browser interaction (client-side scripts/session flow) to reach actual result content, and identify a replayable request pattern if possible.

## Interaction steps performed
1. Launch Chromium with Playwright (headless mode).
2. Open `https://www.court.gov.mo/zh/subpage/researchjudgments`.
3. Wait for DOM/content idle state so controls are interactive.
4. Fill only minimal date-range fields (recent 30 days).
5. Click the search button.
6. Wait for transition/network stabilization.
7. Save page snapshots and network logs.

## Observed page transition
- Capture pre-submit HTML (`playwright_before_submit.html`).
- Trigger submit via browser click.
- Capture post-submit HTML and screenshot (`playwright_after_submit.html`, `playwright_after_submit.png`).
- Record final URL and frame navigation events for evidence of transition/reload.

## Observed network behavior
- Log all request events with URL, method, resource type, and POST data (if available).
- Also log request-finished and request-failed events to preserve status/failure context.
- Persist into `playwright_network_log.json`.

## Likely search request candidate
Candidate priority:
1. POST request containing payload after submit.
2. Otherwise, URL containing search-related keywords (e.g., `search`, `research`, `query`, `result`, `judgment`).

The probe report must include candidate URL/method and POST-data preview (if present).

## Whether browser interaction is required
Determine from combined evidence:
- whether browser submit succeeded,
- whether post-submit page shows apparent result markers,
- whether submission-like request appears only under browser flow.

If requests-only probes still return form fallback while browser flow shows richer transition/network calls, treat browser interaction as currently required.

## Recommended next step decision
- **If clear replayable request is captured** (stable endpoint + payload/session hints): proceed with targeted `requests` replay validation.
- **If replay remains unclear or bound to dynamic browser state**: continue with Playwright-based result extraction (probe-level first, no full crawler yet).
