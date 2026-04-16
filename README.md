# MO_cocounsel

**Macau Legal Copilot / 澳門版 CoCounsel（retrieval-first portfolio prototype）**

MO_cocounsel is a **Macau legal research system prototype** built on top of **public Macau court judgments**.  
The project direction is explicit:

> **Build the retrieval engine first. Add agent workflows later.**

This repository is no longer just a concept note. It already contains a working research pipeline surface, API-facing response envelope, endpoint tests, and a frontend demo integration layer.

---

## 1. Project Positioning

MO_cocounsel is positioned as a:

- **Macau Legal Copilot**
- **Macau CoCounsel-style research prototype**
- **retrieval-first legal AI portfolio project**

Current focus:

- legal research over Macau public judgments
- metadata-aware case presentation
- provenance-preserving research output
- API/demo productization

Current non-focus:

- premature multi-agent orchestration
- broad drafting automation as the main delivery layer
- “chatbot first” packaging without retrieval rigor

---

## 2. What Is Already Built

### Crawling / Corpus
Completed work includes:

- court result-page probing
- selector-driven result parsing
- text detail extraction
- raw corpus layout
- pagination extension
- all-court crawling mode
- duplicate-strategy fixes
- zh / pt / pdf / txt link handling

### Retrieval / Research Pipeline
Completed work includes:

- chunking prep
- BM25 prep
- local BM25 query prototype
- issue decomposition layer
- hybrid retrieval skeleton
- citation binding layer
- answer synthesis skeleton
- structured research output schema
- search router
- exact case-number lookup refinement
- Portuguese / mixed-query routing refinement
- route-specific evaluation slices

### Metadata
Completed work includes:

- metadata target schema
- deterministic metadata baseline
- metadata field evaluation
- model-generated metadata comparison harness
- local metadata generation connection
- Traditional Chinese normalization
- latest valid artifact selection fix
- metadata integration into the research pipeline

### Product / API / Demo
Completed work includes:

- case-card / UI-ready output layer
- API-ready response envelope
- FastAPI integration surface
- endpoint validation tests
- frontend demo integration
- filter / sort / compact case-card layout refinement

---

## 3. Data Source

Primary source:

- Macau Courts public judgment search page  
  https://www.court.gov.mo/zh/subpage/researchjudgments

Known source characteristics already accounted for in the project:

- `court` parameters: `tui` / `tsi` / `tjb` / `ta` / `all`
- page turning via `&page=`
- `court=all` is useful for broad coverage and demo use, but not ideal as the final full-harvest strategy
- a more complete long-term harvest strategy should be **per-court crawling + merge/dedupe**
- sentence / TXT pages are important authoritative text sources
- records may be zh-only, pt-only, or mixed-language

---

## 4. Core Technical Decisions

### Metadata source preference
For retrieved cases:

- prefer **model-generated metadata** when available
- otherwise fallback to **deterministic baseline**
- always preserve `metadata_source`
- keep provenance visible through pipeline, case cards, and API output

### Deterministic baseline stays
The deterministic baseline is **not** legacy dead code. It remains valuable as:

- fallback
- benchmark
- regression guard

### Current local metadata model
Current default local model:

- `qwen2.5:3b-instruct`

This repo currently treats that as the fixed default, not something to casually swap on feel.

### Artifact selection consistency
Metadata-consuming components should share one latest-valid-artifact selection rule:

- explicit override path first
- otherwise auto-select latest valid output

### Traditional Chinese normalization
Model-generated Chinese metadata is normalized to Traditional Chinese, without breaking structured fields such as:

- case numbers
- URLs
- source chunk ids

---

## 5. Current API Surface

### `POST /api/research/query`

The current minimal FastAPI integration surface is implemented in:

- `app/api/research.py`

It exposes the existing research pipeline through a response envelope built from the case-card layer.

### Request shape

```json
{
  "query": "假釋",
  "top_k": 5
}
```

### Response envelope

The response model includes:

- `schema_version`
- `query`
- `top_k`
- `result_count`
- `diagnostics`
- `results`

Diagnostics include:

- `retrieved_cases_count`
- `case_cards_built`
- `model_generated_metadata_used_count`
- `deterministic_fallback_used_count`
- `success_flag`
- `selected_model_metadata_path`
- `selected_model_metadata_case_count`

This design makes the output inspectable and demo-friendly, instead of returning only a bare answer paragraph.

---

## 6. Frontend Demo

The repository includes a browser demo file:

- `frontend/demo_research_integration.html`

The current demo supports:

- query input
- `top_k` input
- result summary panel
- diagnostics panel
- compact case-card rendering
- filtering by:
  - `metadata_source`
  - `language`
- sorting by:
  - `authoritative_decision_date`
  - `authoritative_case_number`
- progressive disclosure for long fields

Suggested demo queries currently used in the project:

- `假釋`
- `量刑過重`
- `253/2026`

These cover:

- legal-concept retrieval
- issue/argument-style retrieval
- exact case-number lookup

---

## 7. Validated Repository Files

This README is aligned to repository files that already exist in the codebase, including:

- `app/api/research.py`
- `app/schemas/research.py`
- `crawler/pipeline/build_api_ready_response_envelope.py`
- `frontend/demo_research_integration.html`
- `tests/test_research_endpoint.py`
- `docs/day52_acceptance.md`
- `docs/day54_acceptance.md`
- `docs/day55_acceptance.md`
- `docs/day56_acceptance.md`
- `docs/day57_acceptance.md`
- `docs/day58_acceptance.md`

So the current repo state is best understood as:

> **a working retrieval/product prototype with documented milestone delivery, not just a future architecture proposal.**

---

## 8. Minimal Local Usage

### A. Build an API-ready research envelope from the pipeline

Confirmed CLI entrypoint:

```bash
python crawler/pipeline/build_api_ready_response_envelope.py --query "假釋" --top_k 5 --json
```

This produces an API-ready response envelope over the existing UI-ready case-card layer.

### B. Run endpoint tests

Confirmed test file:

```bash
pytest tests/test_research_endpoint.py
```

The test coverage includes:

- happy-path request validation
- missing query validation
- invalid `top_k` validation
- blank-query validation

---

## 9. Research Output Shape

At the current stage, the project is moving toward a structured legal research package rather than a flat list of search hits.

The response layer is already designed around:

- case cards
- authoritative case number
- decision date
- court
- language
- case type
- case summary
- holding
- legal basis
- disputed issues
- metadata source
- source links
- card title / subtitle / tags

This is a better product foundation than a plain text answer because it preserves:

- inspection
- filtering
- sorting
- provenance
- UI productization

---

## 10. Current Strengths

What this repository already shows well:

- retrieval-first product discipline
- pipeline thinking instead of UI-first thinking
- legal-source grounding awareness
- metadata provenance design
- explicit fallback logic
- multilingual routing awareness
- API surface design
- frontend demo packaging
- milestone-based delivery progression

For portfolio purposes, this is materially stronger than a generic “LLM + chat UI” demo.

---

## 11. Current Limitations

This prototype still has real limitations:

1. **RAG quality is not fully hardened yet**  
   Retrieval quality, citation quality, and synthesis quality still need tightening.

2. **Model-generated metadata does not yet cover the full corpus**  
   Coverage is still partial rather than complete.

3. **Portuguese / mixed-query routing remains weaker than the strongest slices**  
   This is a known improvement path, not an unknown failure.

4. **`court=all` is useful but not the final corpus strategy**  
   Long-term harvesting should move toward per-court crawl + merge/dedupe.

5. **Agent workflows are intentionally not the main line yet**  
   The project is still prioritizing a reliable research substrate.

---

## 12. Why This Project Matters

MO_cocounsel is valuable because it is trying to solve the hard part first:

- source ingestion
- retrieval structure
- metadata quality strategy
- evidence-linked presentation
- API/demo integration

That makes it a portfolio project about:

- retrieval engineering
- legal AI product design
- metadata systems
- pipeline hardening
- backend integration
- demo-oriented productization

—not just about putting a language model behind a text box.

---

## 13. Near-Term Roadmap

Current next-stage priorities are:

- pipeline quality hardening
- metadata coverage expansion
- stronger integration consistency
- demo/API/frontend polish for presentation

Not the current priority:

- jumping early into large multi-agent orchestration
- changing the default metadata model without benchmark-driven reason

---

## 14. One-Line Summary

**MO_cocounsel is a retrieval-first Macau legal research prototype built on public court judgments, with metadata-aware case cards, an API-ready response envelope, endpoint tests, and a frontend demo integration layer.**
