# Day 51 Acceptance

## Today objective

Build a local case-card / UI-ready structured output layer on top of the metadata-integrated research pipeline.

## Deliverables

- `crawler/pipeline/build_case_card_ui_ready_output.py`
- `crawler/pipeline/build_case_card_ui_ready_output_spec.md`
- `docs/day51_acceptance.md`
- local report output path:
  - `data/eval/case_card_ui_ready_output_report.txt`

## Acceptance checklist

- [ ] Existing metadata-integrated research pipeline is called from the Day 51 layer.
- [ ] Retrieved enriched cases are transformed into UI-ready case-card records.
- [ ] Every case card includes required fields:
  - authoritative_case_number
  - authoritative_decision_date
  - court
  - language
  - case_type
  - case_summary
  - holding
  - legal_basis
  - disputed_issues
  - metadata_source
  - pdf_url
  - text_url_or_action
  - card_title
  - card_subtitle
  - card_tags
- [ ] CLI supports `--query` and `--top_k`.
- [ ] Terminal output includes required counters and success status.
- [ ] No default model switch and no candidate-promotion logic changes.
- [ ] No vector retrieval, DB integration, external API, or cloud model usage introduced.
- [ ] No large generated artifacts committed.

## Evidence developer must provide

1. Command used to run Day 51 case-card output builder.
2. Terminal output showing:
   - query received
   - retrieved cases count
   - case cards built
   - model-generated metadata used count
   - deterministic fallback used count
   - whether case-card UI-ready output appears successful
3. Confirmation that report was written to:
   - `data/eval/case_card_ui_ready_output_report.txt`
4. Git diff showing only code/docs changes and no large generated outputs.
