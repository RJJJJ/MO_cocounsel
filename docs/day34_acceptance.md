# Day 34 Acceptance - Local Deterministic Search Router Layer

## Today objective

Build a deterministic local search router layer before retrieval that classifies legal query types and chooses the corresponding retrieval strategy.

## Deliverables

1. `crawler/retrieval/search_router_layer.py`
   - deterministic query classification
   - routing decision payload
   - local demo runner that routes first, then calls an existing retrieval flow
2. `crawler/retrieval/search_router_layer_spec.md`
   - design rationale, query classes, routing rules, limitations, next steps
3. local demo output generation
   - `data/eval/search_router_demo_report.txt` generated for acceptance evidence
   - avoid committing large generated artifacts

## Acceptance checklist

- [ ] Local-only implementation (no DB, no external API, no LLM).
- [ ] Identifies all required query classes:
  - [ ] `case_number_lookup`
  - [ ] `single_legal_concept`
  - [ ] `multi_issue_legal_query`
  - [ ] `mixed_fact_legal_query`
  - [ ] `portuguese_or_mixed`
  - [ ] `ambiguous_or_noisy`
- [ ] Router result contains required fields:
  - [ ] `original_query`
  - [ ] `normalized_query`
  - [ ] `query_type`
  - [ ] `routing_strategy`
  - [ ] `decomposition_recommended`
  - [ ] `retrieval_mode`
- [ ] Demo terminal output includes:
  - [ ] query received
  - [ ] query_type
  - [ ] routing_strategy
  - [ ] decomposition recommended
  - [ ] retrieval mode used
  - [ ] whether search router layer appears successful
- [ ] Demo report written to `data/eval/search_router_demo_report.txt`.
- [ ] No README changes.
- [ ] No vector retrieval implementation.
- [ ] No DB integration.
- [ ] No LLM integration.

## Evidence developer must provide

1. Command used to run router demo, including full query string.
2. Terminal output snippet showing routing decision and success flag.
3. Confirmation that `data/eval/search_router_demo_report.txt` was generated locally.
4. Git diff summary showing only code/docs changes (no large generated artifacts).
