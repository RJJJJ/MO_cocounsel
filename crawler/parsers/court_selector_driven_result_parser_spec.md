# Day 17 Spec: Selector-Driven Macau Courts Result Parser

## Confirmed DOM Structure

Confirmed rendered result-card structure:

```text
div.maincontent
  -> div.case
    -> ul
      -> div
        -> ul
          -> div#zh-language-case.case_list
            -> li
```

Authoritative result root used by parser:
- `div.maincontent`
- `div.case`
- `div#zh-language-case.case_list`

Authoritative card boundary:
- `div#zh-language-case.case_list > li`

## Why `li` is the authoritative card boundary

DOM verification now confirms each real judgment result card is one direct `li` child of
`div#zh-language-case.case_list`. Because this structure is stable and explicit, Day 17 switches
from heuristic block guessing to strict selector parsing.

This removes ambiguity introduced by nested wrapper blocks and repeated layout nodes.

## Why `.seperate` must be excluded

Some `li` elements are not judgment cards and act only as visual separators with class
`seperate`. Keeping them would pollute card counts and field completeness metrics.

Therefore, parser skips any `li` where class contains `seperate`, and also skips trivial/empty
text nodes.

## Exact field selectors within each card (`li`)

- decision date: `span.date`
- case number: `span.num`
- case type: `span.type`
- document links: `span.download a`

## Href-based document classification rules

Primary classification is based on `href` (not visible anchor text):

- zh TXT/fulltext:
  - `href` contains `/sentence/zh/` and does **not** end with `.pdf`
  - set `text_url_zh`
- pt TXT/fulltext:
  - `href` contains `/sentence/pt/` and does **not** end with `.pdf`
  - set `text_url_pt`
- PDF:
  - `href` contains `/sentence/` and ends with `.pdf`
  - zh PDF: `/sentence/zh-...pdf` -> `pdf_url_zh`
  - pt PDF: `/sentence/pt-...pdf` -> `pdf_url_pt`
  - other PDF remains eligible only for primary fallback

Link-preservation behavior:
- preserve full per-card link coverage in `document_links`:
  - `{"kind":"text","language":"zh","url":"..."}`
  - `{"kind":"text","language":"pt","url":"..."}`
  - `{"kind":"pdf","language":"zh","url":"..."}`
  - `{"kind":"pdf","language":"pt","url":"..."}`
- primary convenience fields:
  - `text_url_primary`: zh text first, otherwise pt text.
  - `pdf_url_primary`: zh PDF first, then pt PDF, then other PDF.
- backward compatibility aliases are retained:
  - `text_url_or_action` maps to `text_url_primary`
  - `pdf_url` maps to `pdf_url_primary`

## Duplicate handling for selector-driven output

Deduplication must preserve bilingual source identity:

1. use sorted set of all text URLs on the card (`text_url_zh`, `text_url_pt`);
2. if text set is empty, use sorted set of available PDF URLs;
3. metadata fields remain part of the key (`court`, `case_number`, `decision_date`).

This avoids collapsing cards with different link sets.

## Deferred fields (detail-page phase)

The following fields are intentionally deferred and set to `null` in Day 17 result-card parser:

- `subject`
- `summary`
- `decision_result`
- `reporting_judge`
- `assistant_judges`

Reason: these fields are less stable at list-card level and should be extracted from detail pages.

## Recommended next step

1. Batch text-detail extraction from the selector-driven card outputs.
2. Optionally add pt-language root parsing if a separate Portuguese list root is confirmed.
