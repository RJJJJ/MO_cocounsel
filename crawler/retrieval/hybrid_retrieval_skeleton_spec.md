# Hybrid Retrieval Skeleton Spec (Day 27)

## Why this architecture skeleton is now the next priority

The current local BM25 baseline is already functional for chunk-level retrieval. The next highest-leverage step is to stabilize retrieval interfaces before introducing dense retrieval and reranking complexity. A clean hybrid skeleton lets us evolve retrieval quality without repeatedly rewriting pipeline glue code.

This is especially important because upcoming stages (vector retrieval, reranking, issue decomposition, citation binding) should plug into predictable interfaces and shared result schema.

## Current active component (BM25 only)

For Day 27, the hybrid flow keeps **BM25 as the only active retriever**:

1. Query enters the orchestration layer.
2. Query normalization hook optionally rewrites/expands the query.
3. BM25 retriever runs against local prepared chunks.
4. Dense retriever placeholder returns empty list (intentional no-op).
5. Fusion interface executes in BM25-first pass-through mode.
6. Rerank hook runs as identity function (no-op).

No vector retrieval, no database, and no external API are used.

## Placeholder interfaces for future expansion

The skeleton defines stable interfaces for:

- `QueryNormalizer`
- `BM25Retriever`
- `DenseRetrieverPlaceholder`
- `FusionStrategy`
- `RerankHook`
- `HybridRetriever` orchestration

These placeholders are intentionally simple but enforce explicit component boundaries.

## Retrieval hit schema (citation-ready)

Every retrieval hit follows a consistent schema:

- `chunk_id`
- `score`
- `retrieval_source` (currently `"bm25"`)
- `authoritative_case_number`
- `authoritative_decision_date`
- `court`
- `language`
- `case_type`
- `chunk_text_preview`
- `pdf_url`
- `text_url_or_action`

This schema supports citation-friendly answer assembly and future source binding.

## Integration path for future hybrid retrieval

Planned extension sequence:

1. Replace `LocalDenseRetrieverPlaceholder` with a local dense retriever implementation.
2. Upgrade fusion from BM25 pass-through to weighted / RRF style merge.
3. Attach reranker implementation through `RerankHook`.
4. Add issue decomposition before retrieval (query decomposition hook).
5. Add citation binder after retrieval to map final answer spans to hit metadata.

Because these extension points are explicit, each step can be added with minimal disruption to existing callers.

## Recommended next step

Pick one of the following for Day 28:

1. **Add local dense retrieval stub**
   - Generate deterministic pseudo-embeddings or term-overlap proxy vectors locally.
   - Keep same `DenseRetrieverPlaceholder` interface, but return non-empty candidates.

2. **Add citation binding layer**
   - Build a lightweight binder that maps answer snippets to `chunk_id`, case number, and court/date fields.
   - Keep retrieval unchanged while improving downstream answer traceability.
