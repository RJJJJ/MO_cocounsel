# Court Judgment Search Source Spec (Probe Stage)

## Source name
- Macau Court Judgment Search (裁判檢索)

## Source URL
- https://www.court.gov.mo/zh/subpage/researchjudgments

## Purpose in MVP
- Validate whether the public search interface can be reliably accessed and interpreted with a simple HTTP GET workflow.
- Define the minimum field expectations for Day 3 parsing design.
- Provide a decision gate for selecting `requests` versus browser automation.

## Search page fields observed
> Probe-stage note: fields below are inferred from page labels and keyword checks; full DOM mapping is **to be confirmed**.

- Court / 法院 (observed label keyword)
- Type / 種類 (observed label keyword)
- Case number / 案件編號 (observed label keyword)
- Judgment date / 宣判日期 (observed label keyword)
- Full judgment text / 裁判書全文 (observed label keyword)
- Additional controls: unknown / to be confirmed

## Expected result list fields
> Not parsed in Day 2 probe. All fields are unknown / to be confirmed by Day 3 result-page inspection.

- Result item title: unknown / to be confirmed
- Court: unknown / to be confirmed
- Case number: unknown / to be confirmed
- Judgment date: unknown / to be confirmed
- Document link(s): unknown / to be confirmed
- Pagination metadata: unknown / to be confirmed

## Expected detail page fields
> Not parsed in Day 2 probe. Fields remain unknown / to be confirmed.

- Detail page URL pattern: unknown / to be confirmed
- Case metadata block: unknown / to be confirmed
- Judgment content container: unknown / to be confirmed
- Language variants: unknown / to be confirmed

## Expected linked judgment document fields
> Not parsed in Day 2 probe. Fields remain unknown / to be confirmed.

- Document type (HTML/PDF/DOC): unknown / to be confirmed
- Download URL pattern: unknown / to be confirmed
- File naming convention: unknown / to be confirmed
- Text encoding consistency: unknown / to be confirmed

## Risks / uncertainties
- Page may rely on JavaScript for submitting search and/or rendering result lists.
- Anti-bot controls, cookies, or dynamic tokens may be required for queries.
- Charset handling may vary across Traditional Chinese content.
- Result structure may differ by language selection or court type.
- Probe only confirms static fetchability, not full search execution behavior.

## Decision gate

### Evidence to stay with `requests`
- GET fetch consistently returns complete and correctly encoded HTML.
- Search form inputs and submission endpoints can be identified from static HTML.
- Result list and detail links are present in server-rendered responses.
- No mandatory dynamic token or runtime-generated parameters block request replay.

### Evidence to move to Playwright
- Critical search/result DOM appears only after JavaScript execution.
- Form submission requires client-side generated payloads not reproducible from static requests.
- Request flow depends on dynamic anti-bot challenges or scripted navigation state.
- Static GET provides shell HTML without parseable data needed by MVP.
