# Day 19 Raw Corpus Layout Spec (Macau Court Cases)

## Why raw corpus layout is the next priority after Day 18

Day 18 validated that selector-card-driven detail extraction is stable (27/27 successful, 0 failed). The immediate next priority is to turn this extraction output into a durable, append-friendly raw corpus format so:

- future pagination batches can be added without restructuring old data,
- each case has a stable on-disk home,
- downstream chunking/indexing can read from a single normalized source of truth.

## Directory structure design

```text
data/corpus/raw/macau_court_cases/
  manifest.jsonl
  raw_corpus_build_report.txt
  cases/
    <language>/
      <year>/
        <case_number_slug>/
          metadata.json
          full_text.txt
```

Design choices:

- `language` (e.g. `zh`, `pt`) is a first-level partition for bilingual management.
- `year` is derived from authoritative decision date, enabling temporal slicing.
- `case_number_slug` provides a stable case folder key safe for filesystem paths.
- `metadata.json` stores record-level source and normalization information.
- `full_text.txt` stores only extracted body text (UTF-8).
- `manifest.jsonl` acts as a global index for fast lookup and future ingestion.

## Metadata authority rules

For each record, the metadata from the source list is considered authoritative:

- `authoritative_case_number = source_list_case_number`
- `authoritative_decision_date = source_list_decision_date`

`metadata.json` includes (minimum):

- `court`
- `source_list_case_number`
- `source_list_decision_date`
- `source_list_case_type`
- `language`
- `pdf_url`
- `text_url_or_action`
- `page_number`
- `extraction_source` (e.g., `day18_selector_card_batch`, `day20_pagination_extension`)
- `full_text_path`

## Naming / slug rules

- case folder name is based on authoritative case number.
- slug normalization:
  - lowercase
  - replace non `[0-9a-z]` chars with `_`
  - collapse repeated `_`
  - trim leading/trailing `_`
- empty result fallback: `unknown_case_<index>`
- directory collision fallback: append duplicate suffix (e.g. `__dup2`).

## Manifest design

`manifest.jsonl` has one line per case and includes key retrieval fields:

- `language`
- `authoritative_case_number`
- `authoritative_decision_date`
- `court`
- `pdf_url`
- `text_url_or_action`
- `metadata_path`
- `full_text_path`

This keeps a compact searchable ledger while detailed fields remain in `metadata.json`.

## How future pagination batches should append into this layout

When new pages are extracted:

1. Produce the same normalized fields as Day 18 outputs.
2. Resolve authoritative fields with the same rules (strictly from list-page metadata).
3. Generate language/year/slug target folder.
4. If same case already exists, either:
   - skip (if exact duplicate policy), or
   - version/replace per ingestion policy.
5. Append a new line to `manifest.jsonl` only for accepted new corpus records.
6. Update build/append report with counts and duplicate handling details.

Recommended operationally:

- keep builder idempotent for full rebuilds,
- add a future `append` mode for incremental pagination runs.

## Recommended next step

After Day 19 storage normalization, choose one of:

1. **Extend pagination range** to enlarge corpus coverage while preserving this layout.
2. **Build chunking + indexing prep layer** that reads from `manifest.jsonl` and `full_text.txt` without changing raw storage conventions.