# Search Router Layer Spec (Day 34)

## Why search routing is now the next priority

Day 33 completed structured research output formatting, so we now have a stable output contract for downstream product surfaces. The next highest product-value step is reducing retrieval mismatch by routing different query shapes into more suitable retrieval paths before retrieval execution.

Without routing, all queries are pushed through one generic retrieval path. That causes lower precision for case-number lookups and unnecessary missed coverage for multi-issue legal questions that should use decomposition-aware fan-out.

## Supported query classes

The local deterministic router currently classifies each query into exactly one class:

1. `case_number_lookup`
2. `single_legal_concept`
3. `multi_issue_legal_query`
4. `mixed_fact_legal_query`
5. `portuguese_or_mixed`
6. `ambiguous_or_noisy`

## Routing decision rules

The router is deterministic, rule-based, and local-only:

- `case_number_lookup`
  - Trigger: case number regex hit (e.g. `123/2024`).
  - Strategy: `prefer_exact_case_number_path_then_hybrid_fallback`.
  - Decomposition: off.
  - Retrieval mode: `exact_case_number_heavy_bm25`.

- `single_legal_concept`
  - Trigger: one legal concept keyword and no mixed fact/legal indicators.
  - Strategy: `direct_hybrid_skeleton_bm25_first`.
  - Decomposition: off.
  - Retrieval mode: `direct_bm25_or_hybrid_skeleton`.

- `multi_issue_legal_query`
  - Trigger: multiple legal concept hints and/or legal concepts with connector-heavy phrasing.
  - Strategy: `decomposition_aware_hybrid_retrieval`.
  - Decomposition: on.
  - Retrieval mode: `decomposition_aware_bm25_hybrid`.

- `mixed_fact_legal_query`
  - Trigger: both legal concept hints and fact-pattern hints.
  - Strategy: `decomposition_aware_hybrid_retrieval`.
  - Decomposition: on.
  - Retrieval mode: `decomposition_aware_bm25_hybrid`.

- `portuguese_or_mixed`
  - Trigger: Portuguese legal lexicon hit or explicit mixed CJK + alphabetic language signal.
  - Strategy: `language_aware_bm25_path`.
  - Decomposition: off.
  - Retrieval mode: `bm25_language_aware`.

- `ambiguous_or_noisy`
  - Trigger: short/noisy/non-specific query that does not satisfy other class rules.
  - Strategy: `conservative_direct_retrieval`.
  - Decomposition: off.
  - Retrieval mode: `conservative_direct_bm25`.

## Relationship with decomposition and hybrid retrieval

The router does not replace retrieval; it decides which existing local retrieval flow to call:

- Direct path: `HybridRetriever` (`hybrid_retrieval_skeleton.py`).
- Decomposition-aware path: `DecompositionAwareHybridRetriever` (`hybrid_retrieval_with_decomposition.py`).

Therefore, Day 34 adds orchestration value without introducing new remote dependencies, databases, or dense retrieval execution.

## Current limitations

- Rule-based keyword coverage is intentionally narrow and may under-classify edge phrasing.
- Case-number matching currently focuses on `N/YYYY` shape only.
- Portuguese detection is lexical and heuristic, not full language identification.
- No learning-to-route or confidence scoring yet.
- Retrieval mode labels are routing intents; dense retrieval remains inactive.

## Recommended next step

Choose one of the following as Day 35+:

1. Add a local dense retrieval stub to improve route-specific fusion testing while keeping local-only constraints.
2. Refine the exact case-number lookup path (pattern coverage + deterministic case-id scoring) for stronger precision on citation-heavy legal workflows.
