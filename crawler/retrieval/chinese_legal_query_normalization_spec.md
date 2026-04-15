# Chinese Legal Query Normalization Spec (Day 26)

## Why this is now the top priority

Day 25 local retrieval evaluation shows a stable pattern:
- `legal_concept_zh` strong
- `case_number_lookup` strong
- `issue_fact_zh` weaker
- `portuguese_or_mixed` weak

Because the local corpus and BM25 pipeline already produce usable hits, the next bottleneck is query-side normalization quality (especially Chinese legal phrasing and case-number variants).

## Normalization rules implemented

The new normalization layer (`improve_chinese_legal_query_normalization.py`) is deterministic and local-only.

1. **Unicode normalization**
   - `NFKC` canonicalization to reduce Unicode compatibility variance.

2. **Full-width / half-width normalization**
   - Normalizes full-width symbols (`／`, `（`, `）`, `，`, `。` etc.) to half-width ASCII equivalents.

3. **Common punctuation normalization**
   - Canonical punctuation replacement and whitespace collapse.

4. **Case-number formatting normalization**
   - Canonicalizes forms like:
     - `79/2025`
     - `79 / 2025`
     - `第79/2025號`
   - Output canonical form: `79/2025` (or `1087/2025/a` with suffixes).

5. **Chinese legal phrasing variants**
   - Maps high-frequency variant expressions to canonical query phrases.
   - Example families:
     - `合同之不能履行` / `合約不能履行` / `不能履行合同` -> `合同不能履行`
     - `量刑明顯過重` / `刑罰過重` / `判刑過重` -> `量刑過重`
     - `賠償損失` / `損失賠償` -> `損害賠償`

6. **Common legal synonym / variant mapping**
   - Adds lightweight, deterministic canonical mapping table for Chinese legal terms (Traditional + selected Simplified variants).

7. **Simple query expansion for high-value terms**
   - Adds deterministic lexical expansion when a canonical legal term appears.
   - Examples:
     - `假釋` -> add `提前釋放`, `刑法典第56條`
     - `量刑過重` -> add `量刑明顯過重`, `刑罰過重`, `改判`
     - `損害賠償` -> add `賠償損失`, `損失賠償`, `民事賠償`

## Legal synonym / variant handling strategy

- Use **deterministic dictionary-based normalization**, not embedding/vector expansion.
- Prefer **precision-preserving canonical replacements** first, then **small high-value expansion lists**.
- Keep expansions domain-specific and short to avoid BM25 noise inflation.
- Do not call external APIs or services.

## Case-number normalization rules

- Regex captures optional markers/padding/spacing and normalizes to `<num>/<year>` (+ optional suffix).
- Handles Chinese-style wrappers like `第...號`.
- Collapses whitespace around separators.
- Keeps matching robust to user formatting habits.

## Limitations

- Rule list is curated and finite; unseen variants are not auto-learned.
- Portuguese/mixed queries are only indirectly improved.
- No semantic disambiguation for highly ambiguous legal concepts.
- Expansion may still over-broaden some queries if not tuned by eval slices.

## Recommended next step

Choose one of:
1. **Build hybrid retrieval layer skeleton** (BM25 + re-ranker interface, still local-first).
2. **Improve Portuguese/mixed query handling further** with dedicated pt normalization and cross-lingual legal term mapping.
