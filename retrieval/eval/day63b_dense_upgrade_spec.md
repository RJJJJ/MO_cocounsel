# Day 63B Dense Upgrade Spec (bge-m3)

## Why Day 63B is inserted before Day 64

Day 63 dense-only baseline used `chargram_hash_v1` and reached only 50% pass rate on the Day 61 regression pack. Before Day 64 fusion, we need a stronger dense signal so fusion experiments measure *fusion quality* rather than weak dense encoder quality.

## Why whole-case-only dense retrieval is not the main retrieval unit

- Existing retrieval pipeline and regression pack are chunk-first.
- Whole-case-only retrieval would change retrieval granularity and confound Day 64 comparison.
- Day 63B therefore keeps chunk-level retrieval units and only upgrades semantic embedding quality.

## Source-of-truth policy

1. Source of truth is latest `data/corpus/raw/macau_court_cases_full/manifest.jsonl`.
2. Build Day 63B dense-ready chunks from full corpus via:
   - `crawler/prep/build_day63b_dense_ready_chunks.py`
3. Dense index build consumes the refreshed chunk-level artifact, not legacy non-full-corpus chunk snapshots.

## bge-m3 selection rationale

- `BAAI/bge-m3` is a multilingual embedding model suitable for zh/pt/mixed legal queries.
- Single-model scope keeps Day 63B lightweight and avoids multi-model bake-off expansion.
- Day 63B runs in local-only mode with small batch settings.

## Embedding text design

Each chunk embedding text is composed as:

- authoritative_case_number
- court
- language
- case_type
- chunk_text

This improves semantic grounding while retaining chunk context. Exact case-number lookup is still treated as BM25 guardrail zone, not as dense-only strength.

## Artifact layout

- Dense-ready chunk input:
  - `data/corpus/prepared/macau_court_cases/dense_baseline/day63b_dense_ready_chunks.jsonl`
- Dense index artifact:
  - `data/corpus/prepared/macau_court_cases/dense_baseline/day63b_bge_m3_index.json`
- Regression outputs:
  - `data/eval/day63b_dense_retrieval_results.json`
  - `data/eval/day63b_dense_retrieval_summary.txt`
  - `data/eval/day63b_dense_vs_baselines_comparison.txt`

## Known limitations

- Runtime requires local `FlagEmbedding` + model availability for `BAAI/bge-m3`.
- Build can be slow on CPU due to full chunk corpus embedding.
- Dense-only still expected to underperform BM25 on strict exact case-number lookup.

## Recommended next step

Proceed to **Day 64 score fusion** using BM25 guardrails + Day63B dense signal as additive relevance evidence.
