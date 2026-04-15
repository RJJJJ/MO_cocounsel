# Day 29 Acceptance - Answer Synthesis Skeleton

## Today objective

Build a local deterministic answer synthesis skeleton on top of the existing hybrid retrieval + citation binding pipeline, producing a structured legal research draft without introducing dense retrieval, database integration, or LLM generation.

## Deliverables

1. `crawler/retrieval/answer_synthesis_skeleton.py`
   - Receives query input.
   - Calls existing hybrid retrieval skeleton.
   - Calls existing citation binding layer.
   - Generates deterministic structured draft with:
     - `query`
     - `answer_type=structured_research_draft`
     - `provisional_summary`
     - `key_findings`
     - `cited_sources`
     - optional `source_notes`
   - Includes local demo runner and report writer.

2. `crawler/retrieval/answer_synthesis_skeleton_spec.md`
   - Captures rationale, strategy, schema, citation usage rules, limitations, and next-step options.

3. `data/eval/answer_synthesis_demo_report.txt`
   - Local demo report with required run evidence.

## Acceptance checklist

- [ ] Local-only answer synthesis logic implemented.
- [ ] No database access added.
- [ ] No external API access added.
- [ ] No LLM calls added.
- [ ] Retrieval main flow is unchanged.
- [ ] Citation binding main flow is unchanged.
- [ ] Draft output includes required fields:
  - `query`
  - `answer_type`
  - `provisional_summary`
  - `key_findings`
  - `cited_sources`
  - optional `source_notes`
- [ ] `provisional_summary` is template-based and clearly marked as draft / retrieval-grounded.
- [ ] `key_findings` includes 3-5 finding items sourced from chunk previews.
- [ ] Each finding references at least one citation label.
- [ ] `cited_sources` preserves citation fields:
  - `citation_label`
  - `chunk_id`
  - `pdf_url`
  - `text_url_or_action`
- [ ] Demo terminal output includes:
  - query received
  - retrieval hits used
  - citation records used
  - answer draft generated
  - whether answer synthesis skeleton appears successful
- [ ] No large generated artifacts are included in git diff.

## Evidence developer must provide

- Command used to run the local answer synthesis demo.
- Terminal output snippet with the required five lines.
- Path to generated demo report: `data/eval/answer_synthesis_demo_report.txt`.
- `git status` snippet showing only intended code/docs/report changes.
