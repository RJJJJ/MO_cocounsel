# Local BM25 Query Prototype Spec (Day 23)

## Why query validation is now more important than more crawling
Day 21 (chunking prep) and Day 22 (BM25 prep) already produced a queryable local foundation. At this stage, adding more crawl volume without validating retrieval quality increases data size but does not prove that users can actually find relevant judgments. For the Macau court use case, query behavior validation is now the bottleneck because:

1. Corpus language is mixed (Chinese + Portuguese), and naive whitespace tokenization fails for Chinese legal terms.
2. Legal users frequently search by case numbers/references, so exact and normalized reference handling must be verified.
3. Product value depends on top-k relevance and traceability, not only corpus completeness.

Therefore Day 23 focuses on a local, deterministic query prototype that exposes ranking behavior and output schema clearly.

## Chosen tokenizer strategy for Chinese / mixed zh-pt text
Default strategy: `deterministic_regex_plus_cjk_bigrams`.

It combines:

1. **Regex extraction for Latin-script terms**
   - captures Portuguese/Latin words (`acórdão`, `recurso`, etc.)
2. **Regex extraction for alphanumeric citation-like references**
   - keeps tokens such as `123/2020`, `tsi-45-2021`, `cr3-99/19`
3. **Case-number normalization**
   - collapses whitespace around references and preserves slash format for matching
4. **CJK-friendly deterministic tokenization**
   - generates Chinese character bigrams over contiguous CJK sequences to avoid whitespace dependency

Optional enhancement:
- `--tokenizer auto` or `--tokenizer jieba` can include local `jieba` segmentation if installed.
- The default path remains fully runnable without external services or mandatory extra dependencies.

## How case-number queries are handled
The prototype supports case-number-like queries in two ways:

1. **Tokenizer preservation**: case-like patterns are extracted as dedicated tokens (e.g., `123/2020`).
2. **Ranking bonus**: when query contains case-reference tokens and they appear in `authoritative_case_number`, an explicit deterministic bonus is added.

This improves practical legal lookup behavior where case numbers often dominate user intent.

## Ranking output schema
Each returned hit includes:

- `score`
- `chunk_id`
- `authoritative_case_number`
- `authoritative_decision_date`
- `court`
- `language`
- `case_type`
- `chunk_text_preview`
- `pdf_url`
- `text_url_or_action`

This preserves source traceability and makes local QA possible without database/API integration.

## Limitations of the baseline
1. Pure lexical BM25 cannot resolve semantic equivalence across different legal phrasing.
2. Chinese bigram strategy is robust but simplistic versus domain-tuned segmenters.
3. Cross-lingual relevance (zh query vs pt text) remains limited without translation/semantic methods.
4. Ranking uses local in-memory indexing and is not optimized for very large corpus scale.

## Recommended next step
Choose one of the following according to roadmap priority:

1. **All-court crawling mode**
   - broaden recall coverage once retrieval behavior is validated.
2. **Hybrid retrieval layer (BM25 + future vector)**
   - keep BM25 traceability while improving semantic matching for zh/pt legal language.
