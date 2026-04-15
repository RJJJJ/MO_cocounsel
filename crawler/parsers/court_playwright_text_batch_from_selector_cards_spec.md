# Day 18 Spec: batch text-detail extraction from selector-driven cards

## Why selector-driven result cards are the stable entry layer

Day 17 established a deterministic parser that reads each result card from fixed, verified selectors (`div#zh-language-case.case_list > li`) and preserves key list metadata and detail links. This provides a stable and repeatable entry layer for downstream extraction, avoiding earlier block-scoring ambiguity and card-boundary drift.

## Why detail extraction is body-first (not complex selector-first)

For Macau Courts sentence/TXT pages, practical DOM inspection shows content is mostly flat and directly rendered in `<body>` with many `<br>` tags, rather than consistently wrapped inside rich semantic containers such as `article`, `main`, or nested content components.

Therefore the extraction strategy is:

1. clone/read body content;
2. remove noise nodes (scripts/styles) and print chrome;
3. extract body-level visible text (`innerText`/`textContent` fallback);
4. normalize whitespace + blank lines;
5. parse metadata from normalized text.

This reduces fragility versus selector-first extraction on pages without stable semantic wrappers.

## Print block handling

The parser explicitly removes/ignores print chrome patterns:

- small top-right block commonly styled with `float: right;`;
- print anchor text such as `打印全文`, `Imprimir`, `Print`;
- links/elements with `onclick="window.print()"`.

It also performs a post-normalization cleanup pass to remove leftover one-line print artifacts.

## Metadata parsing rules from normalized body text

After normalized body text is produced, regex-based parsing extracts:

- `detail_case_number` from patterns such as:
  - `第79/2025號案`
  - `卷宗編號: 122/2025`
  - `案號: 123/2025`
- `detail_decision_date` from patterns such as:
  - `日期: 2025年12月12日`
  - `日期：2026年3月26日`
  - date fallback formats (`DD/MM/YYYY`, `YYYY年M月D日`)
- `detail_title_or_issue` from:
  - `關鍵詞:` / `關鍵字:` lines
  - `重要法律問題:` lines
  - optional short top headline fallback before major section tokens

If title/issue is not clearly separable, value remains `null`.

## Source metadata vs detail metadata reconciliation

Each output record retains source-layer fields for debugging/comparison:

- `court`
- `source_list_case_number`
- `source_list_decision_date`
- `source_list_case_type`
- `pdf_url`
- `text_url_or_action`
- `page_number`

Detail-layer fields are extracted separately:

- `detail_case_number`
- `detail_decision_date`
- `detail_title_or_issue`
- `language`
- `full_text`

Rule: detail-page metadata is authoritative when successfully parsed; source-list metadata remains as a non-authoritative reference.

## Quality checks

Batch run output includes:

- total selector cards read
- cards with usable `text_url_or_action`
- total detail pages attempted / succeeded / failed
- `zh` count / `pt` count
- average `full_text` length
- whether extraction appears successful

Per-record quality gate requires non-empty `full_text` with minimum length/token thresholds and print-chrome exclusion.

## Recommended next step

Choose one of:

1. build raw corpus storage layout for long-term sentence-text assets and traceability; or
2. extend pagination/range to increase harvested coverage now that Day 18 batch extraction path is stable.
