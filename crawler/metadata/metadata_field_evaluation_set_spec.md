# Metadata Field Evaluation Set Spec (Day 40)

## Why metadata field evaluation is now the next priority

Day 38 defined the target metadata schema, and Day 39 implemented a deterministic extraction baseline. The immediate next step is to measure output quality **field by field** with a small, human-checkable benchmark. Without this layer, we cannot tell whether future extraction changes improve or regress quality on core digest fields.

This Day 40 scope is intentionally narrow:
- build a compact benchmark set
- build a local runner with stable scoring
- keep everything local-only and reproducible

## Field definitions

The benchmark evaluates four generated digest fields:

- `case_summary`: short narrative summary of the case background/legal context.
- `holding`: the operative disposition/result by the court.
- `legal_basis`: legal provisions/articles relied on in the decision.
- `disputed_issues`: the core issues/questions in dispute.

Each benchmark row includes:
- `authoritative_case_number`
- `language`
- `court`
- `expected_case_summary`
- `expected_holding`
- `expected_legal_basis`
- `expected_disputed_issues`
- optional `notes`

## Evaluation set design

- File: `data/eval/metadata_field_evaluation_set.jsonl`
- Built by: `crawler/metadata/build_metadata_field_evaluation_set.py`
- Size: 8 curated cases (small but representative)
- Language coverage: `zh` and `pt`
- Selection principle: relatively stable, easy-to-manually-verify cases from current corpus

Why small:
- fast human review
- low maintenance for iterative local testing
- enough variation to expose obvious rule-quality gaps across fields and languages

## Comparison strategy per field

Implemented in `crawler/metadata/run_metadata_field_evaluation.py`.

### 1) Field coverage
For each field, compute the fraction of evaluated cases where prediction is non-empty.

### 2) `legal_basis`
- `exact_match_avg`: exact list equality score averaged by case
- `normalized_overlap_avg`: normalized set overlap (case-folding, punctuation/spacing normalization)

### 3) `disputed_issues`
- `exact_match_avg`: exact list equality score averaged by case
- `normalized_overlap_avg`: normalized set overlap score averaged by case

### 4) `case_summary` / `holding`
Because these are free text fields:
- `loose_text_overlap_avg`: token overlap ratio on normalized text
- `containment_signal_avg`: binary containment signal (`expected in predicted` or `predicted in expected`)

The report also outputs:
- weakest field (based on primary aggregate quality signal)
- whether evaluation appears successful (simple threshold gate for local regression checks)

## Limitations of the small benchmark

- small sample size; not statistically comprehensive
- expected texts are concise human references, not exhaustive gold summaries
- legal basis normalization is rule-based and may miss citation variants
- disputed issues may still be noisy in source texts; benchmark cannot cover all edge cases
- no semantic model-based scoring (deliberately omitted this round)

## Recommended next step

After Day 40, proceed with one of:

1. **Improve deterministic metadata extraction rules (recommended first)**
   - tighten heading boundaries
   - reduce summary bleed into `disputed_issues`
   - normalize legal citation variants more aggressively

2. **Add a local dense retrieval stub (optional later)**
   - only after deterministic baseline reaches acceptable stability on this benchmark
   - keep local-only and measurable with the same field-level evaluation harness
