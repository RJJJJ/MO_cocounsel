# Day 9 Result-Card Parser Spec (Macau Courts)

## Why the old exploratory parser was insufficient

Day 8 parser used a generic mixed-block strategy (table/list/div scanning) and treated many repeated layout blocks as potential results. That caused false positives from page chrome (navigation, wrappers, utility links), and the extracted JSON did not reliably represent real judgment records.

For Day 9, parser behavior is narrowed to a deterministic **result-card** target only.

## Confirmed result-card structure (from manual inspection)

Each judgment result appears as a repeated card-like block with:

1. **Top row**:
   - judgment/decision date
   - case number
   - category/case type
   - document links (PDF + text/fulltext)
2. **Middle content**:
   - subject section
   - summary section
3. **Lower metadata area**:
   - decision result
   - reporting judge
   - assistant judges

## Field mapping plan

The parser maps one card to one JSON object:

- `court`
  - inferred from page context (fallback `unknown`; current heuristic allows `中級法院` if detected)
- `decision_date`
  - regex-driven extraction from card text
- `case_number`
  - regex-driven extraction from card text
- `case_type`
  - heuristic extraction from top-line text after case number
- `pdf_url`
  - first anchor matching pdf hints (`pdf`, `.pdf`)
- `text_url`
  - first anchor matching text/fulltext hints (`全文`, `text`, `fulltext`, etc.)
- `subject`
  - label-based extraction using subject keywords
- `summary`
  - label-based extraction using summary keywords
- `decision_result`
  - label-based extraction using decision-result keywords
- `reporting_judge`
  - label-based extraction using reporting-judge keywords
- `assistant_judges`
  - label-based extraction using assistant-judge keywords
- `raw_card_text`
  - normalized full text for traceability/debugging

## Assumptions and uncertainties

- The replay HTML contains repeated containers for true cards (same tag/class signature).
- Card labels may appear in Chinese or Portuguese variants; keyword list is intentionally multilingual but still heuristic.
- Case type placement may vary by card template; fallback may be partial.
- If the page context does not explicitly include court text, `court=unknown` is expected.

## Extraction quality goals

- Prioritize **precision** over recall for card detection.
- Avoid generic top-level wrappers by requiring repeated containers plus card quality scoring.
- Provide field hit counts and a high-level quality gate (`looks_like_true_judgment_cards`) to surface parser confidence.

## Recommended next step

Choose one focused increment after Day 9:

1. **Parse text detail pages** (recommended first):
   - follow `text_url`
   - extract full judgment body and structured holdings
2. **Add pagination**:
   - preserve same deterministic card parser per page
   - aggregate multi-page results while deduplicating by case/date/id
