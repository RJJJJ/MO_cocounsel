# Day 50 Acceptance

## Today objective

Integrate case-level generated metadata into the actual local research pipeline output, with explicit source preference and fallback behavior.

## Deliverables

- `crawler/pipeline/integrate_metadata_into_research_pipeline.py`
- `crawler/pipeline/integrate_metadata_into_research_pipeline_spec.md`
- `docs/day50_acceptance.md`
- minimal Day 42 comparison harness path-selection fix (latest output/input convenience)
- local report output path:
  - `data/eval/integrated_metadata_research_pipeline_report.txt`

## Acceptance checklist

- [ ] Retrieval flow is executed from query input.
- [ ] Retrieved cases are enriched with case-level metadata.
- [ ] Metadata source preference is model-generated first.
- [ ] Deterministic baseline fallback works when model metadata is unavailable.
- [ ] Each enriched case item includes required metadata fields and source tag.
- [ ] CLI supports `--query` and `--top_k`.
- [ ] Console output includes required counters and success status.
- [ ] No model default switch and no candidate-promotion logic changes.
- [ ] No large generated artifacts are committed.

## Evidence developer must provide

1. Command used to run metadata-integrated pipeline.
2. Terminal output showing:
   - query received
   - retrieved cases count
   - cases enriched with metadata
   - model-generated metadata used count
   - deterministic fallback used count
   - whether metadata-integrated research pipeline appears successful
3. Confirmation that report was written to:
   - `data/eval/integrated_metadata_research_pipeline_report.txt`
4. Git diff showing only code/docs (and small text report if included), with no large generated outputs.
