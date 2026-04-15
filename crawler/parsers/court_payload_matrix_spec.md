# Court Payload Matrix Spec (Day 5)

## Endpoint under test
- Primary endpoint comes from Day 3 `form_fields.json` selected form `action` resolved against source URL.
- Fallback endpoint: `https://www.court.gov.mo/zh/subpage/researchjudgments`.

## Tested payload variants
For each tested date format, the probe generates and executes these payload families:

1. **A. token + date range only**
   - Hidden/token fields from form metadata.
   - Date range fields (`from`, `to`) for the most recent 30 days.
2. **B. token + date range + court**
   - Variant A + one non-empty court select value.
3. **C. token + date range + court + ProcType**
   - Variant B + one non-empty procedure-type select value.
4. **D. token + date range + court + one keyword in recContent**
   - Variant B + one keyword value (`合同`) in the recContent-like field.

## Tested date formats
- `YYYY-MM-DD`
- `YYYY/MM/DD`

## Comparison criteria
Each payload variant report records:
- payload name
- payload keys
- response status
- final URL
- response length
- whether page still looks like search form
- whether page appears to contain candidate case/result markers

Additional scoring signals used internally:
- search form marker hit count
- candidate marker hit count
- case number regex hit count

## Observed best payload
- Defined as the payload variant with highest probe score in `payload_matrix_report.json`.
- The score prefers:
  - more case/result marker hits
  - fewer search-form markers
  - not looking like search-form fallback
  - successful HTTP response

## Remaining unknowns
- Whether the server requires additional anti-CSRF/session states not represented in static form metadata.
- Whether some fields require specific option combinations rather than single-option sampling.
- Whether the endpoint response requires follow-up request flow (e.g., redirect + state token refresh).
- Whether response HTML includes dynamic placeholders that mimic results but are not stable result rows.

## Next-step recommendation
- If at least one variant stops looking like a search-form fallback and shows stronger candidate markers, continue with `requests` and deepen HTML structure parsing.
- Otherwise, escalate the probe strategy (non-Playwright options first, such as session-state preflight and option matrix expansion).
