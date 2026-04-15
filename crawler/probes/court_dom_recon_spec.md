# Day 16C DOM reconnaissance spec (Macau Courts)

## Why reconnaissance is needed now
- Search-flow automation (open page → select court → submit → paginate → open TXT) is already proven, but list-page metadata parsing has been unstable across multiple fixes.
- The immediate risk is overfitting parser logic to static HTML snapshots rather than the actual rendered browser DOM.
- This round isolates one task: reconnaissance only, to generate selector candidates and structural notes before any parser refactor.

## Likely result-card container selectors (to validate from probe output)
- Repeated block signatures with high heuristic score (date/case/pdf/txt presence):
  - `div#...<class group>` repeated >= 3
  - `li#...<class group>` repeated >= 3
  - `tr#...<class group>` repeated >= 3 (if table-like rendering appears)
- Candidate ranking dimensions:
  - repetition count
  - text-length distribution consistency
  - date-like text hits
  - case-number-like text hits
  - PDF link presence
  - TXT/fulltext link presence

## Likely header selectors inside each card
- Semantic headers: `h1`, `h2`, `h3`, `header`
- Class-based headers: `.title`, `.case-title`, `.card-header`, `.panel-heading`
- Fallback heuristic:
  - highest-density short text node near top of candidate card
  - sibling proximity to case number / date fields

## Likely PDF/TXT link selectors
- Anchor baseline:
  - `a[href*='pdf' i]`
  - `a[href*='txt' i]`
  - `a[href*='text' i]`
- Text-label fallback:
  - `a:has-text('全文')`
  - `a:has-text('Text')`
  - `a:has-text('Teor')`
- Normalization rule:
  - always resolve relative href with `urljoin(BASE_URL, href)` before downstream use.

## Likely sentence-page metadata selectors
- Zone-level candidates:
  - `main section`, `article section`, `div.meta`, `div.metadata`, `table`, `dl`
- Field-level candidates (post-recon):
  - case number: text contains `案號` / `案件編號` or pattern like `123/2024`
  - date: text matches `YYYY-MM-DD`, `DD/MM/YYYY`, or `YYYY年M月D日`
  - title/issue: text contains `主題` / `爭點` / `摘要` / `subject` / `issue` / `sumário`

## Likely sentence-page main-body selectors
- Primary candidates:
  - `main`, `article`, `.content`, `.judgment-content`, `.sentence-content`, `pre`, long `div`
- Body heuristics:
  - large text length (e.g., >= 800)
  - multiple paragraphs (`p` count)
  - high non-empty line count
  - low link density compared with result cards

## Recommended parser design after reconnaissance
1. **Two-stage selector strategy**
   - Stage A: pick container signature by repeated-structure score.
   - Stage B: field extraction within container using label-driven + regex fallback.
2. **Selector registry with confidence ranking**
   - Keep top N selectors per field (case/date/title/pdf/txt/body), each with confidence and last-seen evidence.
3. **DOM-first validation gate**
   - Before extraction, validate candidate container count and key-field hit-rate; fail fast if below threshold.
4. **Separation of concerns**
   - Keep result-page parser and sentence-page parser isolated; share only text normalization and regex utilities.
5. **Regression fixtures from artifacts**
   - Use `dom_recon_*` HTML and candidate JSON as baseline fixtures for parser tests in the next round.
