# Portuguese / Mixed Query Routing Refinement Spec (Day 36)

## Why this is now the next priority

Day 35 strengthened exact case-number lookup and Day 34 introduced a deterministic router. At this point, manual checks show local BM25 can already retrieve some Portuguese legal queries reasonably. The main gap is query-side routing and normalization quality: Portuguese and mixed Chinese-Portuguese queries were still too often pushed toward `ambiguous_or_noisy`.

Therefore Day 36 focuses on **deterministic local routing/normalization refinement** rather than retrieval infrastructure changes.

## Supported Portuguese / mixed query patterns

The refined logic explicitly supports:

1. **Pure Portuguese legal query**
   - examples: `erro ostensivo`, `legis artis`, `liberdade condicional`
2. **Portuguese case-style query**
   - examples: `processo n o 578/2025 recurso em matéria cível`
3. **Mixed Chinese-Portuguese legal query**
   - examples: `假釋 liberdade condicional`
4. **Portuguese legal terminology mixed with case number**
   - examples: `processo 253/2026 liberdade condicional`

## Language-signal detection rules

Implemented in `portuguese_mixed_query_normalization.py`.

1. **Normalization rules**
   - Unicode NFKC normalization.
   - Normalize spacing around `/` in case numbers.
   - Normalize common `processo n o` / `processo n.º` variants to `processo nº`.
   - Collapse repeated spaces.

2. **Portuguese legal lexicon detection**
   - Deterministic term matching over curated lexicon (e.g., `acórdão`, `processo`, `recurso`, `liberdade condicional`, `erro ostensivo`, `legis artis`, `matéria cível`).

3. **Mixed-language heuristic**
   - Detect CJK characters and Latin-word count.
   - Mark mixed-language when both sides are meaningfully present.

4. **Case-style and case-number signal**
   - Detect case number patterns like `578/2025` and optional suffix.
   - Detect Portuguese case-style hints (`processo nº`, `recurso`, `matéria cível`).

5. **Multi-issue hint (lightweight)**
   - Detect repeated connectors (`e`, `ou`, `以及`, `及`, `;`) for potential decomposition recommendation.

## Routing decisions

Router output now includes language signal traceability via `language_signal_summary`.

1. **Portuguese/mixed + case number**
   - `query_type = case_number_lookup_pt_mixed`
   - `routing_strategy = exact_case_number_heavy_with_pt_context_retention`
   - `retrieval_mode = exact_case_number_heavy_bm25_pt_context`

2. **Portuguese or mixed-language legal query (without dominating case-number path)**
   - `query_type = portuguese_or_mixed` (or `_multi_issue`)
   - `routing_strategy = language_aware_bm25_path`
   - `retrieval_mode = bm25_language_aware_pt_or_mixed`
   - decomposition usually off; can be on only when multi-issue signal is explicit.

3. **Other classes remain deterministic**
   - Existing classes (`single_legal_concept`, `mixed_fact_legal_query`, etc.) are preserved.

## Limitations

- Rule-based lexicon coverage is intentionally small and may miss rare Portuguese legal phrasing.
- Mixed-language detection is heuristic and not a full language ID system.
- No semantic expansion for Portuguese synonyms beyond listed terms.
- No dense retrieval, no DB integration, no external APIs.

## Recommended next step

Choose one of these incremental options:

1. Add a **local dense retrieval stub** (still local, no network dependency) for controlled ablation experiments.
2. Integrate **route-specific retrieval evaluation slices** (pt-only, zh-pt mixed, pt+case-number) to measure whether routing changes produce higher recall@k and MRR.
