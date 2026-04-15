# Day 32 Acceptance - End-to-End Local Research Pipeline Demo

## Today objective
Connect existing local modules into one deterministic end-to-end research pipeline demo:
`query -> issue decomposition -> hybrid retrieval -> citation binding -> answer synthesis`.

## Deliverables

1. `crawler/pipeline/end_to_end_research_pipeline_demo.py`
   - Python local entrypoint.
   - CLI supports:
     - `--query "<text>"`
     - `--top_k 5`
     - `--decompose on/off`
   - Runs optional decomposition stage.
   - Runs decomposition-aware hybrid retrieval.
   - Binds citations from merged retrieval hits.
   - Runs answer synthesis skeleton.
   - Prints required pipeline summary lines.
   - Writes local demo report to:
     - `data/eval/end_to_end_research_pipeline_demo_report.txt`

2. `crawler/pipeline/end_to_end_research_pipeline_demo_spec.md`
   - Documents integration rationale, stage flow, stage handoff data, deterministic constraints, limitations, and next-step recommendation.

3. `docs/day32_acceptance.md`
   - Captures Day 32 objective, deliverables, checklist, and evidence requirements.

## Acceptance checklist

- [ ] End-to-end local pipeline orchestration file is added.
- [ ] Existing decomposition/retrieval/citation/synthesis modules are integrated without rewriting their internals.
- [ ] No database access added.
- [ ] No external API access added.
- [ ] No LLM integration added.
- [ ] No dense retrieval implementation added.
- [ ] CLI supports `--query`, `--top_k`, `--decompose`.
- [ ] Terminal output includes at least:
  - query received
  - decomposition used
  - subqueries generated count
  - retrieval hits after merge
  - citation records generated
  - answer draft generated
  - whether end-to-end research pipeline appears successful
- [ ] Output answer result includes:
  - query
  - decomposition_summary
  - retrieval_summary
  - citation_summary
  - answer_draft
- [ ] `decomposition_summary` includes:
  - main_issue
  - sub_issues
  - retrieval_subqueries
- [ ] `retrieval_summary` includes:
  - hits_used
  - top_case_numbers
- [ ] `citation_summary` includes:
  - citation_labels
  - source_count
- [ ] No large generated artifacts are committed in diff.

## Evidence developer must provide

- Command used to run the Day 32 end-to-end demo locally.
- Terminal output snippet showing all required summary lines.
- Generated local report path:
  - `data/eval/end_to_end_research_pipeline_demo_report.txt`
- `git status` snippet showing only intended code/docs changes committed.
