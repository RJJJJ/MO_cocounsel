# Day 35 Acceptance - Exact Case-Number Lookup Refinement

## Today objective

Improve exact case-number lookup quality and make it a stronger deterministic special-case retrieval path for legal research queries.

## Deliverables

1. `crawler/retrieval/refine_exact_case_number_lookup.py`
   - local-only deterministic exact case-number-heavy retrieval path
   - case-number normalization to canonical form
   - exact match ranking that dominates fallback lexical BM25 matches
   - BM25 fallback only when exact hits are insufficient
   - output includes full source traceability fields
2. `crawler/retrieval/exact_case_number_lookup_spec.md`
   - design rationale, normalization rules, supported forms, fallback strategy, limitations, next-step options
3. local demo report generation
   - `data/eval/exact_case_number_lookup_demo_report.txt`
   - generated locally for acceptance evidence
   - avoid committing large generated artifacts

## Acceptance checklist

- [ ] Local-only implementation (no DB, no external API, no vector retrieval).
- [ ] Supports required case-number forms:
  - [ ] `253/2026`
  - [ ] `253 / 2026`
  - [ ] `第253/2026號`
  - [ ] `1087/2025/A`
  - [ ] `1087 / 2025 / A`
  - [ ] mixed upper/lower suffix variants
- [ ] Query normalization produces canonical case-id.
- [ ] Exact/normalized matches rank above BM25 fallback hits.
- [ ] BM25 fallback can be used when exact hits are insufficient.
- [ ] Each output hit includes:
  - [ ] `chunk_id`
  - [ ] `authoritative_case_number`
  - [ ] `authoritative_decision_date`
  - [ ] `court`
  - [ ] `language`
  - [ ] `case_type`
  - [ ] `pdf_url`
  - [ ] `text_url_or_action`
  - [ ] `score`
  - [ ] `retrieval_source`
- [ ] Demo terminal output includes:
  - [ ] raw query
  - [ ] normalized case query
  - [ ] exact match candidates found
  - [ ] fallback used yes/no
  - [ ] top_k returned
  - [ ] whether exact case-number lookup refinement appears successful
- [ ] No README changes.
- [ ] No large generated artifact committed.

## Evidence developer must provide

1. Command used to run the Day 35 demo query.
2. Terminal output snippet showing normalization, exact candidate count, fallback decision, top-k count, success flag.
3. Confirmation that `data/eval/exact_case_number_lookup_demo_report.txt` was generated locally.
4. Git diff summary showing only code/docs + small acceptance report content.
