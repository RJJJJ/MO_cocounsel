# Repository Navigation Guide

Quick map for maintainers and new AI sessions.

## Top-level responsibility map

- `crawler/`:
  - source probing, crawling, parser flows, corpus prep, metadata tooling, research pipeline scripts.
- `retrieval/`:
  - indexing and evaluation runners/specs, especially Day 61+ retrieval milestones.
- `app/`:
  - FastAPI app entry + API route/schema integration.
- `frontend/`:
  - local demo HTML for integration verification.
- `docs/`:
  - acceptance trail + architecture/status governance docs.
- `data/`:
  - corpus artifacts and eval outputs.

## Corpus layers and relationship

### 1) Authoritative full-case layer (source of truth)

- Location: `data/corpus/raw/macau_court_cases_full/` (plus supporting raw crawl assets).
- Unit: full-case records with authoritative merge/dedupe identity.
- Identity: `sentence_id`.
- Role: upstream authority for all downstream prep and retrieval.

### 2) Prepared retrieval layer (consumption layer)

- Location: `data/corpus/prepared/macau_court_cases/`.
- Unit: chunk-level retrieval records (`chunks.jsonl`, `bm25_chunks.jsonl`, dense-ready chunk artifacts).
- Role: retrieval/indexing/evaluation input layer.

Relation:

- authoritative full-case corpus -> prep scripts -> retrieval chunk corpus.

## Where to find key specs

### Crawler / pipeline / prep specs

- `crawler/pipeline/*_spec.md` (end-to-end flow, API envelope, metadata integration, all-court mode, etc.)
- `crawler/prep/chunking_prep_layer_spec.md`
- `crawler/prep/bm25_prep_layer_spec.md`
- `crawler/storage/raw_corpus_layout_spec.md`

### Retrieval specs + eval

- `retrieval/eval/day61_regression_pack_spec.md`
- `retrieval/eval/day62_bm25_strengthening_spec.md`
- `retrieval/eval/day63_dense_baseline_spec.md`
- `retrieval/eval/day63b_dense_upgrade_spec.md`

### Acceptance and status docs

- Latest milestones:
  - `docs/day61_acceptance.md`
  - `docs/day62_acceptance.md`
  - `docs/day63_acceptance.md`
  - `docs/day63b_acceptance.md`
- Snapshot docs:
  - `docs/project_status_snapshot.md`
  - `docs/index.md`

## App / API / demo entry points

- API app: `app/main.py`
- API route: `app/api/research.py`
- Request/response schema: `app/schemas/research.py`
- Demo page: `frontend/demo_research_integration.html`

## Eval artifacts and reports

- Primary location: `data/eval/`
- Day 61/62/63/63B summaries and comparisons are stored as `*.txt` + `*.json` artifacts.
- Use these artifacts as empirical status evidence before declaring milestone completion.

## Practical handoff reading order (recommended)

1. `README.md`
2. `docs/project_status_snapshot.md`
3. `docs/dependencies_and_runtime.md`
4. `docs/repo_navigation.md`
5. milestone-specific acceptance/spec docs for the day you continue from
