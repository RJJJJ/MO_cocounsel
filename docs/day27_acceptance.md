# Day 27 Acceptance - Hybrid Retrieval Layer Skeleton

## Today objective

Build a local hybrid retrieval skeleton with stable interfaces on top of the current BM25 baseline, while keeping BM25 as the only active retriever.

## Deliverables

- `crawler/retrieval/hybrid_retrieval_skeleton.py`
  - Local-only orchestration flow for hybrid retrieval.
  - Query normalization hook interface.
  - BM25 retriever adapter interface.
  - Dense retriever placeholder interface.
  - Fusion/merge strategy interface.
  - Rerank hook interface.
  - Retrieval hit schema with citation-ready fields.
- `crawler/retrieval/hybrid_retrieval_skeleton_spec.md`
  - Architecture rationale and future integration path.
- Local demo output (small local artifact):
  - `data/eval/hybrid_retrieval_demo_report.txt`

## Acceptance checklist

- [ ] README is unchanged.
- [ ] No database integration added.
- [ ] No external API integration added.
- [ ] No true vector retrieval implementation added.
- [ ] No true reranking implementation added.
- [ ] Hybrid skeleton includes interfaces for:
  - [ ] query normalization
  - [ ] BM25 retrieval
  - [ ] dense retrieval placeholder
  - [ ] fusion strategy
  - [ ] rerank hook
- [ ] Retrieval hit schema includes:
  - [ ] `chunk_id`
  - [ ] `score`
  - [ ] `retrieval_source`
  - [ ] `authoritative_case_number`
  - [ ] `authoritative_decision_date`
  - [ ] `court`
  - [ ] `language`
  - [ ] `case_type`
  - [ ] `chunk_text_preview`
  - [ ] `pdf_url`
  - [ ] `text_url_or_action`
- [ ] Local demo report contains at least:
  - [ ] retrieval mode used
  - [ ] query received
  - [ ] top_k returned
  - [ ] whether hybrid retrieval skeleton appears successful

## Evidence developer must provide

- Commands run for local demo and checks.
- Terminal output snippet confirming:
  - retrieval mode used
  - query received
  - top_k returned
  - hybrid skeleton success flag
- File path of local demo report:
  - `data/eval/hybrid_retrieval_demo_report.txt`
- Git diff summary showing only code/docs/small local report changes and no large generated artifacts.
