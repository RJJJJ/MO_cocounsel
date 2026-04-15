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

After normalized body text is produced, metadata is parsed as a best-effort enrichment layer rather than as a hard dependency for extraction success.

The parser prioritizes stable full-text capture first, then derives detail metadata from the normalized text using light pattern matching and top-of-document heuristics:

- `detail_case_number`
  - inferred from common case-number expressions near the top of the document, such as:
    - `第79/2025號案`
    - `卷宗編號：122/2025`
    - `案件編號: 第253/2026號`
    - `案號: 123/2025`
- `detail_decision_date`
  - inferred from common date expressions near the top of the document, such as:
    - `日期：2026年3月26日`
    - `裁判日期：2026年3月19日`
    - fallback date formats like `DD/MM/YYYY` and `YYYY年M月D日`
- `detail_title_or_issue`
  - inferred from early non-empty lines in the normalized text using weak heuristics
  - when available, colon-style descriptive lines may be used
  - the parser does not require a fixed label vocabulary such as `關鍵詞`, `關鍵字`, `主題`, or `重要法律問題`
  - if no stable issue/title line can be inferred, the value remains `null`

Important rule: metadata parsing must not determine whether the detail page extraction itself succeeds. The primary success criterion is whether a usable `full_text` has been extracted.

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

Rule: detail-page metadata is authoritative when successfully parsed; source-list metadata remains as a non-authoritative reference for debugging and comparison.

Because Macau Courts sentence/TXT pages are semi-structured rather than strictly template-driven, detail metadata is treated as best-effort enrichment. Missing `detail_case_number`, `detail_decision_date`, or `detail_title_or_issue` does not by itself invalidate an otherwise successful text extraction result.

## Quality checks

Batch run output includes:

- total selector cards read
- cards with usable `text_url_or_action`
- total detail pages attempted / succeeded / failed
- `zh` count / `pt` count
- average `full_text` length
- whether extraction appears successful

Per-record quality gate requires non-empty `full_text` with minimum length/token thresholds and print-chrome exclusion. Metadata parsing is not part of the hard success gate; detail pages with valid `full_text` may still retain `null` metadata fields when no stable metadata can be inferred.

## Recommended next step

Choose one of:

1. build raw corpus storage layout for long-term sentence-text assets and traceability; or
2. extend pagination/range to increase harvested coverage now that Day 18 batch extraction path is stable.
