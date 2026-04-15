# Exact Case-Number Lookup Refinement Spec (Day 35)

## Why this is the next priority

Day 34 already classifies `case_number_lookup` queries at the routing layer. The next highest-value retrieval improvement is a deterministic exact case-number path because legal research users often search by docket/case reference and expect near-perfect precision for known numbers.

## Supported query forms

The refinement path supports at least these forms:

- `253/2026`
- `253 / 2026`
- `第253/2026號`
- `1087/2025/A`
- `1087 / 2025 / A`
- mixed suffix case variants like `1087/2025/a` vs `1087/2025/A`

## Normalization rules

1. Convert query text with NFKC normalization (handles full-width characters).
2. Accept optional Chinese wrappers (`第...號`).
3. Canonicalize slash-separated structure into:
   - `number/year`
   - or `number/year/suffix`
4. Trim whitespace around slashes.
5. Remove leading zeros from number; year normalized to 4 digits.
6. Uppercase alphabetic suffix (`a` -> `A`).

## Retrieval strategy: exact first, BM25 fallback second

1. Parse and normalize raw query into canonical case-id.
2. Build local in-memory exact index from prepared corpus metadata (`authoritative_case_number`).
3. Retrieve exact/normalized matches first and assign them dominant scores.
4. If exact path returns insufficient hits, trigger deterministic local BM25 lexical fallback.
5. Keep provenance in each hit via `retrieval_source`:
   - `exact_case_number_match:<canonical_id>`
   - `bm25_fallback`

This ensures exact case-number matches are ranked above all fallback lexical results.

## Output schema (per hit)

- `chunk_id`
- `authoritative_case_number`
- `authoritative_decision_date`
- `court`
- `language`
- `case_type`
- `pdf_url`
- `text_url_or_action`
- `score`
- `retrieval_source`

## Current limitations

- Still local-file only, no production search service integration yet.
- Case-number parser currently assumes slash-separated formats and simple alphabetic suffixes.
- Fallback BM25 is lightweight lexical scoring, not dense/hybrid semantic ranking.
- No Portuguese-specific case-number aliases beyond the current normalized pattern.

## Recommended next step

Pick one immediate direction:

1. Add a local dense retrieval stub (interface-only, no external model/API), then fuse with exact path and BM25 fallback.
2. Refine Portuguese/mixed query routing and query normalization before this exact path is invoked.
