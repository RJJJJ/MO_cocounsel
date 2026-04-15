# Court Playwright Result-Card Extraction Spec (Day 10)

## Why requests HTML parsing was insufficient

Day 7 requests replay proved that the endpoint flow can be replayed, but Day 9 deterministic parsing on saved replay HTML produced zero cards. This indicates the replay snapshot did not reliably preserve the repeated rendered result-card blocks needed for stable extraction. Likely causes include client-side rendering, async hydration, or server responses that differ by browser execution state.

## Why browser DOM extraction is now the chosen path

Manual screenshots show repeated judgment cards are visible in the browser after interaction. Therefore the extractor now treats the browser-rendered DOM as source of truth:

- submit search using Playwright
- wait for page to stabilize
- detect repeated card-like containers directly from in-page DOM
- parse card fields from those rendered containers

This path aligns implementation with what users actually see.

## Observed card structure

From rendered pages and prior probes:

- results appear as repeated blocks with similar container signature (`tag + class`)
- each card usually contains dense text with labels (e.g., 主題 / 摘要 / 裁判結果 / 法官)
- cards usually include one or more document links (`pdf` and/or text/full-content links)
- case number and decision date are commonly present in the card text

## Extraction strategy

1. Open `https://www.court.gov.mo/zh/subpage/researchjudgments` in Playwright.
2. Try selecting `中級法院` (fallback to all courts if selector is not discoverable).
3. Submit search and wait for network + card-count stabilization.
4. Save rendered artifacts:
   - `data/raw/court_probe/playwright_result_page.html`
   - `data/raw/court_probe/playwright_result_page.png`
5. Run in-page DOM scan over repeated block elements (`div/li/article/section/tr`).
6. Keep candidates only when:
   - container signature repeats at least 3 times
   - heuristic score indicates judgment-card-like content (date/case/link/label signals)
7. Parse required fields and emit JSON + report.

## Field mapping plan

Per extracted card text/links, map to:

- `decision_date`: date regex
- `case_number`: case-number regex
- `case_type`: first token after case number as heuristic
- `pdf_url`: anchor containing `pdf`
- `text_url`: anchor matching 全文/text/fulltext/teor
- `subject`: labeled extraction (`主題`/`subject`)
- `summary`: labeled extraction (`摘要`/`summary`)
- `decision_result`: labeled extraction (`裁判結果`/`resultado`)
- `reporting_judge`: labeled extraction (`裁判書製作法官`/`報告法官`/`juiz relator`)
- `assistant_judges`: labeled extraction (`助審法官`/`adjuntos`)
- `raw_card_text`: normalized card text
- `court`: selected-court context + page fallback inference

## Remaining risks

- Court selector or search button labels may vary by locale/update.
- Dynamic loading timing can change, causing unstable initial extraction.
- Card text labels may vary by language or formatting.
- Link patterns may differ (some cards may omit PDF or text links).

## Recommended next step

Choose one follow-up track:

1. **Parse text detail pages** to recover richer structured fields with higher precision.
2. **Add pagination** to gather full result coverage beyond first page.

Current Day 10 scope intentionally excludes both.
