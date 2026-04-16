# Day 53 Acceptance

## Today objective
Fix metadata latest-output / input-path selection logic so comparison and downstream metadata-consuming layers consistently use the correct latest valid model-generated artifact instead of stale outputs.

## Deliverables
- Shared metadata artifact selection utility with explicit-path override and latest-valid auto-selection.
- Updated comparison harness to use shared selection and expose selected path/case count.
- Updated metadata-integrated pipeline, case-card layer, and API-ready envelope to use/propagate selected artifact diagnostics.
- New local verification script:
  - `crawler/metadata/fix_metadata_comparison_harness_latest_output_selection.py`
- New spec:
  - `crawler/metadata/fix_metadata_comparison_harness_latest_output_selection_spec.md`
- Local acceptance report path (generated during run, not required as committed large artifact):
  - `data/eval/fixed_metadata_latest_output_selection_report.txt`

## Acceptance checklist
- [ ] Explicit model metadata path is honored first when passed.
- [ ] Default/sentinel path behavior auto-selects latest **valid** model metadata output.
- [ ] Validity checks include: exists, parseable JSONL, schema-compatible enough, case_count > 0.
- [ ] Comparison harness reads expanded batch artifact (not stale 10-case output).
- [ ] Metadata-integrated pipeline / case-card / API envelope use consistent selected artifact diagnostics.
- [ ] Report prints:
  - selected model metadata output path
  - selected model metadata case count
  - previous stale path detected yes/no
  - whether latest-output selection fix appears successful

## Evidence developer must provide
- Command(s) used to run Day 53 fix verification.
- Terminal output showing the required four lines above.
- Comparison report path and loaded model case count evidence.
- Downstream consistency evidence showing identical selected path propagated to pipeline, case-card, and API envelope diagnostics.
