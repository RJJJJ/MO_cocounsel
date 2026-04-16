# Day 39 Acceptance - Deterministic Metadata Extraction Baseline

## Today objective

Implement a deterministic metadata extraction baseline on top of the Day 38 metadata-generation target schema, focused on case-level digest fields and reproducible local output.

## Deliverables

1. `crawler/metadata/implement_deterministic_metadata_extraction_baseline.py`
   - Local-only deterministic extraction pipeline.
   - No database, no external API, no LLM.
   - Reads prepared corpus input and emits per-case shaped metadata output.
   - Handles required digest fields:
     - `case_summary`
     - `holding`
     - `legal_basis`
     - `disputed_issues`
   - Provides field-level population stats and required terminal summary lines.

2. `crawler/metadata/deterministic_metadata_extraction_baseline_spec.md`
   - Rationale for priority after Day 38.
   - Field-level deterministic rules.
   - zh vs pt handling notes.
   - Fallback/empty handling rules.
   - Limitations and recommended next step.

3. Local demo report:
   - `data/eval/deterministic_metadata_extraction_baseline_report.txt`

## Acceptance checklist

- [ ] Deterministic extractor script exists and runs locally.
- [ ] No DB/API/LLM dependencies introduced.
- [ ] Output includes per-case shaped metadata envelope consistent with Day 38 structure.
- [ ] Required fields are extracted via explicit heuristics.
- [ ] zh and pt rules are both documented and implemented.
- [ ] Fallback behavior is explicit for each required field.
- [ ] Field-level population stats are printed and written to report.
- [ ] Terminal output includes:
  - [ ] `cases processed`
  - [ ] `case_summary populated`
  - [ ] `holding populated`
  - [ ] `legal_basis populated`
  - [ ] `disputed_issues populated`
  - [ ] `whether deterministic metadata extraction baseline appears successful`
- [ ] No vector retrieval work added in this round.
- [ ] No large generated artifacts committed.

## Evidence developer must provide

1. Command used to run baseline extractor.
2. Terminal summary lines showing all required counts and success flag.
3. Snippet or file path of produced report.
4. Diff summary showing only code/docs/small acceptance artifacts are committed.
5. Confirmation that DB/API/LLM/vector retrieval are not introduced.
