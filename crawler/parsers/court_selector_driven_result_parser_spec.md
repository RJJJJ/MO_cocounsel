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
  - set `text_url_or_action` (preferred), `text_url_zh`, `text_link_language=zh`
- pt TXT/fulltext:
  - `href` contains `/sentence/pt/` and does **not** end with `.pdf`
  - set `text_url_pt` and fallback `text_url_or_action` if zh text link not present
- PDF:
  - `href` contains `/sentence/` and ends with `.pdf`
  - if multiple PDFs exist, prefer zh PDF (`/sentence/zh-...pdf`), else pt PDF, else other PDF

Link-priority behavior:
- `pdf_url`: zh PDF first, then pt PDF, then other PDF.
- `text_url_or_action`: zh text first, otherwise pt text.
- keep both `text_url_zh` and `text_url_pt` when both exist.

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
