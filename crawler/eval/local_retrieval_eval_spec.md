# Local Retrieval Evaluation Spec (Day 25)

## Why evaluation is now the next priority

Day 24 expanded coverage to all-court crawling, and Day 24/previous steps already provide:

- all-court raw corpus accumulation,
- chunking preparation layer,
- BM25 preparation layer,
- local BM25 query prototype.

At this stage, the main bottleneck is no longer ingestion architecture, but **retrieval evaluation discipline**. Without a reusable local query test set, retrieval quality changes cannot be measured consistently across iterations.

## Query set design categories

The local query test set (`data/eval/macau_court_query_test_set.jsonl`) should cover at least:

1. **中文法律概念詞**
   - examples: `假釋`, `量刑過重`, `誹謗`, `違令`.
2. **中文爭點/事實詞**
   - examples: `合同之不能履行`, `損害賠償`, `加重詐騙`.
3. **案件編號查詢**
   - examples: `79/2025`, `253/2026`.
4. **葡文或中葡混合查詢**
   - include a small number of Portuguese or mixed-language samples.
5. **可疑/模糊查詢**
   - vague terms used to expose BM25 baseline limits.

Each JSONL row includes:

- `query_id`
- `query`
- `query_type`
- `expected_case_numbers`
- `expected_language` (optional)
- `notes`

## Expected case matching rules

- Matching is based on **authoritative case number exactness**, with normalization that removes whitespace and lowercases text.
- For each query, evaluation checks whether any expected case number appears in retrieved top-k results (`hit@k`).
- Queries without expected case numbers are retained for qualitative inspection but excluded from exact-hit denominator.

## Baseline metrics to track

The local evaluation runner should report:

- total queries loaded,
- total queries evaluated,
- queries with expected case numbers,
- exact case hit count,
- hit@k summary,
- per-query summary (query id/type, expected cases, top returned cases, first hit rank).

## Limitations of current BM25 baseline

- Lexical dependence: misses semantically relevant chunks when wording diverges.
- Query normalization gap for Chinese legal phrasing variants.
- Mixed-language retrieval remains term-overlap dependent.
- Ambiguous short queries (`上訴`, `公司`) often return noisy results.
- No cross-field weighting beyond current BM25 text assembly.

## Recommended next step

Preferred path:

1. improve Chinese legal query normalization (synonyms, phrase normalization, numerals/form variants), then
2. build a hybrid retrieval layer skeleton (BM25 + dense reranking/hybrid orchestration).

This sequence keeps baseline measurable while preparing a controlled upgrade path to hybrid retrieval.
