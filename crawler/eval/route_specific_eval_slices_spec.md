# Route-Specific Evaluation Slices Spec (Day 37)

## Why this is the next priority

After Day 34-36, retrieval is no longer a single monolithic path:
- Day 34 introduced deterministic search routing.
- Day 35 strengthened exact case-number lookup behavior.
- Day 36 refined Portuguese / mixed-language routing.

A single global hit@k now hides route-specific quality gaps. We need route/query-class slices so we can detect which deterministic path is actually underperforming and prioritize fixes with evidence.

## Slice definitions

Day 37 evaluation must at least report these slices:

1. `case_number_lookup`
   - Routed case-number-centric lookups, including PT/mixed case-number variants.
2. `single_legal_concept`
   - One legal concept with low decomposition pressure.
3. `multi_issue_legal_query`
   - Multiple legal issues likely requiring decomposition-aware fan-out.
4. `mixed_fact_legal_query`
   - Queries containing both legal concepts and factual signals.
5. `portuguese_or_mixed`
   - Portuguese-only or mixed-language legal intent.
6. `ambiguous_or_noisy`
   - Underspecified/noisy queries requiring conservative handling.

## How routing output is used in evaluation

For each query in the local test set:

1. Run deterministic router.
2. Capture routing metadata:
   - `query_type`
   - `routing_strategy`
   - `retrieval_mode`
3. Execute the currently selected local retrieval path:
   - exact case-number-heavy retriever for case-number routes
   - decomposition-aware retriever when decomposition is recommended
   - direct hybrid retriever for remaining deterministic direct routes
4. Compute exact case hit and hit@k against expected case numbers.
5. Aggregate metrics by slice.

This keeps evaluation aligned with real route decisions rather than with static labels in the test set.

## Required per-slice outputs

Each slice reports:
- total queries
- queries with expected cases
- exact case hit count
- hit@k
- sample-size note (small-sample warning)

## Limitations when sample counts are small

When slice sample count is small, hit@k is high-variance and unstable. A perfect or poor score with `n < 3` should be treated as directional only, not as a production-quality signal.

## Recommended next step

Choose one of:

1. Add a **local dense retrieval stub** to enable route-level hybrid ablation metrics without changing external dependencies.
2. Build a **metadata-generation/digest layer target schema** so route-level evaluation can segment by richer facets (language, court, case type, temporal buckets, and citation density).
