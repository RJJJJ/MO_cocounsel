# Day 33 Acceptance - Structured Research Output Schema Refinement

## Today objective
Refine the final deterministic answer schema into a more product-accurate structured legal research output on top of the existing end-to-end local pipeline.

## Deliverables

1. `crawler/retrieval/answer_synthesis_skeleton.py`
   - Upgraded to emit `structured_research_output` schema.
   - Uses decomposition output for `main_issue` and `sub_issues`.
   - Adds retrieval overview, preliminary findings, supporting sources, coverage notes, limitations, and next actions.
   - Keeps local-only deterministic behavior.

2. `crawler/retrieval/structured_research_output_spec.md`
   - Documents rationale, schema, citation rules, deterministic limitations, and next-step options.

3. `docs/day33_acceptance.md`
   - Captures objective, deliverables, checklist, and required evidence.

4. Local demo report generated for acceptance only:
   - `data/eval/structured_research_output_demo_report.txt`

## Acceptance checklist

- [ ] Final schema includes at least:
  - `query`
  - `answer_type: structured_research_output`
  - `research_scope`
  - `main_issue`
  - `sub_issues`
  - `retrieval_overview`
  - `preliminary_findings`
  - `supporting_sources`
  - `coverage_notes`
  - `limitations`
  - `next_actions`
- [ ] `main_issue` and `sub_issues` are sourced from decomposition output.
- [ ] `retrieval_overview` includes hits used, citation count, and top case numbers.
- [ ] `preliminary_findings` has 3-5 deterministic findings with citation labels.
- [ ] `supporting_sources` contains citation-ready source objects.
- [ ] Terminal output includes at least:
  - query received
  - answer output generated
  - findings count
  - supporting sources count
  - whether refinement appears successful
- [ ] No database integration added.
- [ ] No external API added.
- [ ] No LLM integration added.
- [ ] No dense retrieval implementation added.
- [ ] No large generated artifact committed to diff.

## Evidence developer must provide

- Command used to run Day 33 local demo.
- Terminal output snippet with all required lines.
- Local report path confirmation:
  - `data/eval/structured_research_output_demo_report.txt`
- `git status` snippet showing only intended code/docs updates and small demo report.
