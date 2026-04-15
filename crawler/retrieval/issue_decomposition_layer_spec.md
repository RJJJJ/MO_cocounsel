# Issue Decomposition Layer Spec (Day 30)

## Why issue decomposition is now the next priority

Day 27 delivered a local hybrid retrieval skeleton, Day 28 delivered deterministic citation binding, and Day 29 delivered deterministic answer synthesis scaffolding. The next product-value step is to better structure legal research intent before retrieval so that multi-issue and mixed-style legal queries can produce stronger candidate evidence.

At this stage, decomposition must remain deterministic and local-only so the team can evaluate behavior stability before introducing any LLM-based planner.

## Scope

- Local-only decomposition layer.
- No database integration.
- No external API calls.
- No LLM calls.
- Input: raw legal query string.
- Output: retrieval-oriented issue decomposition object.
- Does **not** modify the current hybrid retrieval main flow.

## Supported query patterns

1. **Single legal concept**
   - Example: `假釋` / `量刑過重` / `誹謗`
2. **Multiple parallel legal concepts**
   - Example: `量刑過重與緩刑`
3. **Procedure/remedy terms**
   - Example: `上訴` / `撤銷` / `駁回` / `改判`
4. **Case-number query**
   - Example: `253/2026`
5. **Mixed legal + factual terms**
   - Example: `加重詐騙 損害賠償 量刑過重`

## Deterministic decomposition strategy

1. Normalize raw query:
   - trim whitespace
   - normalize punctuation/spaces
2. Extract canonical components with local rule sets:
   - case number patterns (`\d+/\d{4}`)
   - legal concept terms (canonicalized)
   - procedure/remedy terms (canonicalized)
   - fact-oriented terms
3. Select `main_issue` using deterministic priority:
   - legal term > procedure term > short case-number query > fact term > normalized fallback
4. Build `sub_issues` from remaining terms (bounded list).
5. Build `query_terms` as compact term inventory (bounded list).
6. Build `retrieval_subqueries` with bounded expansion:
   - always keep original query
   - keep normalized query (if changed)
   - keep canonicalized issue terms
   - optionally add case-number-targeted query
   - cap total subqueries to avoid retrieval explosion

## Output schema

- `original_query: str`
- `normalized_query: str`
- `main_issue: str`
- `sub_issues: list[str]`
- `query_terms: list[str]`
- `retrieval_subqueries: list[str]`

## How this plugs into future retrieval orchestration

This layer is designed as a **pre-retrieval adapter**:

- raw query → issue decomposition → retrieval subqueries → hybrid retrieval
- can be inserted before BM25/dense retrieval fan-out
- keeps deterministic traceability for evaluation and debugging
- preserves backward compatibility by keeping original query in subqueries

## Recommended next step

Choose one of the following:

1. Integrate issue decomposition into hybrid retrieval flow as an optional pre-processing stage.
2. Add a local dense retrieval stub and combine with decomposition-driven subquery fan-out for controlled fusion tests.
