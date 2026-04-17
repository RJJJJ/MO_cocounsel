# Day 63 Dense Retrieval Baseline Spec

## Goal
Build a **re-runnable, comparable dense retrieval baseline** on top of the current authoritative merged + prepared Macau court chunk corpus, while keeping BM25+ as-is.

## Model selection rationale
Chosen baseline: `chargram_hash_v1` (deterministic hashed char n-gram embedding).

Selection criteria:
- **Multilingual support**: works directly on Unicode characters, no language-specific tokenizer requirement.
- **Chinese support**: includes CJK unigrams plus overlapping n-grams to preserve ideograph signals.
- **Portuguese support**: captures Latin-script morphology and legal phrasing via character n-grams.
- **Local feasibility**: zero heavy runtime dependencies; no GPU and no external model server required.
- **Implementation simplicity**: deterministic, reproducible index build/search flow with a single model configuration.

> Note: this is a practical engineering baseline, not a final SOTA semantic retriever.

## Artifact format / storage plan
- Artifact root: `data/corpus/prepared/macau_court_cases/dense_baseline/`
- Artifact file: `day63_dense_index.json`
- Payload fields:
  - `artifact_version`
  - `model_key`
  - `embedding_dim`
  - `source_path`
  - `total_chunks`
  - `records[]` (chunk metadata + dense vector)

This artifact is reusable for repeated eval runs and can be refreshed by a single build command.

## Retrieval flow
1. Load prepared chunk corpus (`bm25_chunks.jsonl`).
2. Build per-chunk embedding from concatenated retrieval fields.
3. Persist index artifact.
4. At query time, encode query with same embedder.
5. Compute cosine-equivalent dot product (normalized vectors).
6. Return top-k chunk hits in retrieval schema compatible with eval harness.

## Why dense is introduced after BM25 strengthening
- Day 61/62 established a stable lexical baseline (exact case-number path + strengthened BM25).
- Day 63 adds a parallel semantic path for controlled A/B comparison.
- This sequencing keeps regression safety while preparing Day 64 fusion.

## Expected strengths
- Better robustness on paraphrase-like concept queries.
- Better tolerance for zh/pt mixed wording shifts that do not share exact tokens.
- Stable local reproducibility across runs.

## Expected weaknesses
- Exact case-number retrieval remains weaker than dedicated lexical matching.
- No cross-encoder rerank and no BM25 fusion yet.
- Character hashing embeddings may underperform learned multilingual encoders.

## Known limitations
- Dense baseline is single-route only (no hybrid score fusion in Day 63).
- No ANN acceleration; current corpus size still allows brute-force scoring.
- Embedding quality is intentionally baseline-grade for local feasibility.

## Recommended next step (Day 64)
Implement **BM25 + dense score fusion** (e.g., weighted score merge / RRF) while preserving exact case-number safety behavior and Day 61 regression guardrails.
