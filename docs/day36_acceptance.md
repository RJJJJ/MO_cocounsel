# Day 36 Acceptance - Portuguese / Mixed Query Routing and Normalization Refinement

## Today objective

Improve deterministic recognition and routing quality for Portuguese legal queries and mixed Chinese-Portuguese legal queries, with focus on reducing false `ambiguous_or_noisy` outcomes.

## Deliverables

1. `crawler/retrieval/refine_portuguese_mixed_query_routing.py`
   - local-only refinement demo runner for Portuguese/mixed routing
   - no DB, no external API, no vector retrieval
   - outputs language signals + routing decision fields
2. `crawler/retrieval/search_router_layer.py`
   - updated deterministic routing logic for Portuguese/mixed and case-number+Portuguese patterns
   - router result includes `language_signal_summary`
3. query normalization helper updates
   - deterministic Portuguese/mixed normalization + language signal detection
4. local demo report
   - `data/eval/portuguese_mixed_query_routing_demo_report.txt`
   - generated locally for acceptance evidence
   - no large generated artifact committed
5. `crawler/retrieval/portuguese_mixed_query_routing_spec.md`
   - rationale, supported patterns, detection rules, routing decisions, limitations, next step

## Acceptance checklist

- [ ] Local-only implementation (no DB, no external API, no vector retrieval).
- [ ] Supports required query types:
  - [ ] pure Portuguese legal query (`erro ostensivo`, `legis artis`)
  - [ ] Portuguese case-style query (`processo n o 578/2025 recurso em matéria cível`)
  - [ ] mixed zh-pt query (`假釋 liberdade condicional`)
  - [ ] Portuguese legal terminology mixed with case number
- [ ] Router result contains required fields:
  - [ ] `original_query`
  - [ ] `normalized_query`
  - [ ] `query_type`
  - [ ] `routing_strategy`
  - [ ] `decomposition_recommended`
  - [ ] `retrieval_mode`
  - [ ] `language_signal_summary`
- [ ] Portuguese/mixed queries are not easily downgraded to `ambiguous_or_noisy`.
- [ ] Case-number + Portuguese mixed query can route to exact-case-number-heavy path with pt-aware context retention.
- [ ] Demo terminal output includes:
  - [ ] query received
  - [ ] normalized query
  - [ ] detected language signals
  - [ ] query_type
  - [ ] routing_strategy
  - [ ] retrieval_mode
  - [ ] whether refinement appears successful
- [ ] No README changes.
- [ ] No large generated artifact committed.

## Evidence developer must provide

1. Commands used to run Day 36 demo with representative pt/mixed queries.
2. Terminal output snippets showing normalization, language signals, routing strategy, retrieval mode, and success flag.
3. Confirmation that `data/eval/portuguese_mixed_query_routing_demo_report.txt` was generated locally.
4. Git diff summary showing only code/docs and small acceptance report content.
