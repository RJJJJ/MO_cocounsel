# Day 62 BM25+ Strengthening Spec

## What was strengthened

- Query normalization was refined with auditable legal variant/canonical mappings and high-value expansion terms (Chinese + practical Portuguese alignment).
- BM25 lexical retrieval was strengthened with field-aware weighting instead of flat merged-text scoring.
- Chinese lexical matching was strengthened with mixed token strategy: CJK full-sequence + bigrams + legal concept hints.
- Portuguese/mixed queries were strengthened by adding accent-folded lexical variants and cross-lingual variant normalization.
- Exact case-number stability was preserved with explicit case-reference bonus and dedicated high weight on `authoritative_case_number`.

## Why these changes were chosen before dense retrieval

- Current project mainline is retrieval-first with lexical BM25 foundation and passing Day 61 regression baseline.
- Day 62 goal is low-risk, auditable gain without introducing dense infra, fusion, or reranking complexity.
- These changes directly improve concept recall and phrasing robustness while preserving deterministic behavior.

## Tokenization strategy

- Base tokenizer remains deterministic and lightweight.
- Chinese tokenization now includes:
  - CJK bigrams (existing robust baseline)
  - whole CJK-sequence token for phrase-level anchoring
  - legal concept hint tokens (config-driven)
- Portuguese/mixed tokenization includes:
  - original Latin token
  - accent-folded token variant (e.g., `suspensão` + `suspensao`)
- Case references are still explicitly extracted and normalized; no change that weakens case lookup.

## Synonym expansion strategy

- Centralized in `crawler/retrieval/legal_lexical_mappings.py`.
- Two-layer design:
  - `VARIANT_TO_CANONICAL` for deterministic canonicalization.
  - `HIGH_VALUE_EXPANSION` for practical lexical assists on high-value legal concepts.
- Includes practical Chinese colloquial/legal variants and light Chinese↔Portuguese lexical alignment for BM25 recall support.

## Field weighting strategy

- BM25 score aggregation now uses weighted per-field contributions:
  - `authoritative_case_number`: 4.0
  - `case_type`: 2.0
  - `bm25_text`: 1.5
  - `chunk_text`: 1.0
- Rationale:
  - Protect exact case-number routing behavior.
  - Improve concept intent anchoring in case-type and metadata-derived searchable text.
  - Keep chunk text useful but not overwhelming for concept queries.

## Regression validation method

- Re-run command:

```bash
python retrieval/eval/run_day61_regression_pack.py
```

- Compare with Day 61 baseline using:
  - pass-rate parity
  - top-rank movement on key concept slices
  - no exact case-number lookup breakage

## Known limitations

- Still lexical BM25 only; cannot resolve deep semantic paraphrases without token overlap.
- Chinese segmentation remains lightweight and rule-driven (not full linguistic parser).
- Portuguese-heavy ranking may remain sensitive to long chunk lexical density.

## Recommended next step (Day 63)

- Build **Day 63 dense retrieval baseline** as additive path, then evaluate hybrid fusion candidates against this preserved BM25 baseline.
