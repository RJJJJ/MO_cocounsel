# Day 52 Acceptance

## Today objective

Build an API-ready response envelope that wraps the existing Day 51 case-card / UI-ready output without changing retrieval or metadata generation logic.

## Deliverables

- `crawler/pipeline/build_api_ready_response_envelope.py`
- `crawler/pipeline/build_api_ready_response_envelope_spec.md`
- `docs/day52_acceptance.md`
- local report output path:
  - `data/eval/api_ready_response_envelope_report.txt`

## Acceptance checklist

- [ ] Day 52 layer calls the existing Day 51 case-card / UI-ready output layer.
- [ ] Envelope includes required top-level fields:
  - schema_version
  - query
  - top_k
  - result_count
  - diagnostics
  - results
- [ ] `diagnostics` includes required fields:
  - retrieved_cases_count
  - case_cards_built
  - model_generated_metadata_used_count
  - deterministic_fallback_used_count
  - success_flag
- [ ] `results` directly uses Day 51 case-card records.
- [ ] CLI supports `--query` and `--top_k`.
- [ ] Terminal output includes:
  - query received
  - result_count
  - envelope built yes/no
  - whether API-ready response envelope appears successful
- [ ] No default model switch and no candidate-model promotion logic changes.
- [ ] No vector retrieval, DB integration, external API, or cloud model usage introduced.
- [ ] No large generated artifacts committed.

## Evidence developer must provide

1. Command used to run Day 52 API-ready response envelope builder.
2. Terminal output showing:
   - query received
   - result_count
   - envelope built yes/no
   - whether API-ready response envelope appears successful
3. Confirmation that report was written to:
   - `data/eval/api_ready_response_envelope_report.txt`
4. Git diff showing only code/docs changes and no large generated outputs.
