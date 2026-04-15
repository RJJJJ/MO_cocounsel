# Day 32 Spec: End-to-End Local Research Pipeline Demo

## Why end-to-end integration is now the next priority
Day 28 to Day 31 validated key building blocks independently:
- citation binding works on top of retrieval hits,
- answer synthesis skeleton can consume retrieval + citations,
- issue decomposition can structure legal queries,
- decomposition-aware hybrid retrieval can fan out and merge hits.

The next execution risk is **handoff consistency across stages**. We now need one local entrypoint proving that a single query can pass through all layers in sequence without changing core modules.

## Pipeline stages
1. **Query intake**
   - Receive raw user query from CLI (`--query`).
2. **Issue decomposition (optional)**
   - Controlled by `--decompose on/off`.
   - When on, generate `main_issue`, `sub_issues`, and `retrieval_subqueries`.
3. **Hybrid retrieval (decomposition-aware)**
   - Execute local BM25-active hybrid retrieval through decomposition-aware fan-out.
   - Merge and dedupe by `chunk_id` deterministically.
4. **Citation binding**
   - Convert merged retrieval hits into citation-ready records.
5. **Answer synthesis skeleton**
   - Generate deterministic retrieval-grounded draft summary.
6. **Structured reporting**
   - Print stage-level pipeline counters to terminal.
   - Persist local report to `data/eval/end_to_end_research_pipeline_demo_report.txt`.

## Data passed between stages
- **Query intake → decomposition**
  - raw `query` string.
- **Decomposition/retrieval stage output**
  - `retrieval_subqueries`, merged hits, and retrieval counters.
- **Retrieval → citation binding**
  - unified hit records (`chunk_id`, score, case/date/court/source metadata).
- **Citation binding → synthesis**
  - citation labels + source links + chunk previews.
- **Synthesis → final answer result**
  - `answer_draft` plus structured summaries:
    - `decomposition_summary`
    - `retrieval_summary`
    - `citation_summary`

## Deterministic local-only constraints
- Local execution only.
- No database integration.
- No external API calls.
- No LLM/model inference.
- No dense retrieval activation.
- Orchestration/integration only; existing modules stay intact.

## Current limitations without dense retrieval / LLM
- Recall remains BM25-limited for semantically distant paraphrases.
- Answer draft is template-based and not legal reasoning complete.
- Synthesis relies on chunk previews, not full legal argument extraction.
- No confidence calibration or contradiction detection across sources.

## Recommended next step
Pick one near-term path:
1. **Add local dense retrieval stub**
   - Keep deterministic behavior, but provide a pluggable local semantic candidate generator for fusion experiments.
2. **Refine structured research output schema**
   - Extend answer result with explicit sections (facts, issue, rule, analysis, caveats) while preserving retrieval-grounded citations.
