# Day 28 Acceptance - Citation Binding Layer

## Today objective

Build a local citation binding layer on top of the existing hybrid retrieval skeleton so retrieval hits can be transformed into citation-ready records for downstream answer assembly.

## Deliverables

1. `crawler/retrieval/citation_binding_layer.py`
   - Implements local citation binding from retrieval hits to citation-ready records.
   - Adds `citation_label`, `source_rank`, and `source_group_key`.
   - Includes a local demo runner that executes hybrid retrieval and binding.

2. `crawler/retrieval/citation_binding_layer_spec.md`
   - Explains priority rationale, schema, label design, grouping/rank fields, and forward integration.

3. `data/eval/citation_binding_demo_report.txt`
   - Local demo report showing query, retrieval hit count, citation record count, and success indicator.

## Acceptance checklist

- [ ] Citation binding layer is local-only.
- [ ] No database access added.
- [ ] No external API access added.
- [ ] Retrieval main flow remains unchanged.
- [ ] Binder accepts hybrid retrieval hits and outputs citation-ready records.
- [ ] Citation records include all required fields:
  - `chunk_id`
  - `citation_label`
  - `authoritative_case_number`
  - `authoritative_decision_date`
  - `court`
  - `language`
  - `case_type`
  - `pdf_url`
  - `text_url_or_action`
  - `chunk_text_preview`
  - `retrieval_source`
  - `score`
  - `source_rank`
  - `source_group_key`
- [ ] Local demo prints:
  - query received
  - retrieval hits received
  - citation records generated
  - whether citation binding layer appears successful
- [ ] No large generated artifacts included in git diff.

## Evidence developer must provide

- Command used to run local citation binding demo.
- Terminal output snippet containing required four lines.
- Path to generated demo report: `data/eval/citation_binding_demo_report.txt`.
- `git status` snippet confirming only intended code/docs/report changes are included.
