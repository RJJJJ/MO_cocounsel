# Structured Research Output Spec (Day 33)

## Why output schema refinement is now the next priority

Day 32 already proved the local deterministic pipeline can run end-to-end:
`query -> issue decomposition -> hybrid retrieval -> citation binding -> answer synthesis`.

The next highest-value improvement is product-shape quality at the final layer. Instead of returning a generic deterministic draft, we now produce a legal-research-oriented structured output that is easier for downstream UI, analyst review, and acceptance checks.

This step increases product realism without changing retrieval/citation internals and without introducing non-deterministic dependencies.

## Scope and constraints

- Local-only output formatter and deterministic synthesis logic.
- No database integration.
- No external API integration.
- No LLM integration.
- No dense retrieval implementation in this round.
- No rewrite of core retrieval or citation-binding flow.

## New structured output schema

- `query`
- `answer_type` = `structured_research_output`
- `research_scope`
- `main_issue`
- `sub_issues`
- `retrieval_overview`
  - `hits_used`
  - `citation_count`
  - `top_case_numbers`
- `preliminary_findings` (3-5 objects)
  - `finding_text`
  - `citation_labels`
- `supporting_sources` (citation-ready source objects)
  - `citation_label`
  - `chunk_id`
  - `authoritative_case_number`
  - `authoritative_decision_date`
  - `court`
  - `language`
  - `case_type`
  - `retrieval_source`
  - `score`
  - `pdf_url`
  - `text_url_or_action`
- `coverage_notes`
- `limitations`
- `next_actions`

## Citation attachment rules

1. Each preliminary finding must include `citation_labels`.
2. Findings are built from top-ranked bound citation records in deterministic order.
3. `supporting_sources` preserves citation-binding fields with no semantic mutation.
4. Duplicate `chunk_id` entries are deduplicated in `supporting_sources`.
5. If retrieval coverage is low, findings may reuse a supporting citation to maintain minimum finding count.

## Limitations of deterministic synthesis

- No legal reasoning expansion beyond retrieved chunk previews.
- No conflict-resolution logic for divergent authorities.
- No probabilistic confidence or explainability model.
- Coverage depends on sparse retrieval recall and corpus completeness.
- Output remains a retrieval-grounded preliminary artifact, not legal advice.

## Recommended next step

Choose one extension while preserving deterministic evaluability:

1. Add a local dense retrieval stub implementing the same retrieval hit contract for fusion experiments.
2. Add a search router layer to select retrieval strategy by query type (case-number heavy vs. doctrine-heavy).
