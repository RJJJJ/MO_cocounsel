# MO_cocounsel

Macau Legal Copilot prototype (澳門版 CoCounsel), with a **retrieval-first, agent-later** strategy.

## Project overview

MO_cocounsel is an engineering-focused legal research system built on Macau public judgments. The repository prioritizes corpus authority, retrieval quality, and reproducible evaluation before adding heavier agent workflows.

Core stance:

- retrieval engine first
- agent orchestration later
- authoritative corpus discipline over demo-only behavior

## Current architecture and source-of-truth policy

### Source of truth (authoritative layer)

- **Authoritative full-case / merged corpus** is the source of truth.
- Canonical location: `data/corpus/raw/macau_court_cases_full/` (manifest + merged reports).
- Authoritative identity key: **`sentence_id`**.

### Retrieval consumption layer

- Retrieval does not consume raw crawling snapshots directly.
- Retrieval consumes prepared chunk artifacts under `data/corpus/prepared/macau_court_cases/`.
- `chunks.jsonl`, `bm25_chunks.jsonl`, and day63b dense-ready artifacts are the retrieval-facing layer.

### Metadata policy

- Metadata attach happens **after authoritative merge**.
- policy: **model-generated preferred, deterministic fallback retained**.
- current fixed default metadata model: **`qwen2.5:3b-instruct`**.

## Authoritative flow

Authoritative flow used by this repo:

1. per-court convergence crawl
2. merge + dedupe into authoritative corpus
3. retrieval consumption from prepared corpus
4. metadata attach post-merge

This flow is documented across `docs/crawling_strategy.md` and Day 59/60 acceptance docs.

## Current retrieval stack status

- BM25+ lexical retrieval path is the current stable default path.
- Day 63 introduced a dense baseline (`chargram_hash_v1`) as a baseline-only milestone.
- Day 63B introduces bge-m3 dense upgrade scaffolding + eval scripts.
- Day 64 is planned for score fusion (BM25 guardrails + dense signal), not yet started as accepted implementation.

## Milestone snapshot (latest)

- **Day 61**: retrieval regression pack accepted (10/10 pass).
- **Day 62**: BM25+ strengthening accepted (still 10/10 pass).
- **Day 63**: dense baseline established; dense-only pass rate remained 50% (baseline sense complete, not production default).
- **Day 63B**: in progress; bge-m3 path/spec/scaffolding added, but runtime may be blocked by FlagEmbedding runtime dependency.

## Current roadmap snapshot

- Day 61: ✅ completed
- Day 62: ✅ completed
- Day 63: ✅ completed (baseline milestone)
- Day 63B: 🚧 in progress
- Day 64: ⏭ planned next (score fusion)

## Repo structure overview

- `crawler/`: crawl/probe/parser/prep/pipeline/metadata/retrieval utilities and specs.
- `retrieval/`: indexing and evaluation runners/specs for Day 61+ milestones.
- `app/`: FastAPI integration surface and schema.
- `frontend/`: local demo HTML integration.
- `docs/`: acceptance docs and project governance documents.
- `data/corpus/raw/`: raw and authoritative full-case artifacts.
- `data/corpus/prepared/`: retrieval-consumable chunk corpus and BM25/dense artifacts.
- `data/eval/`: evaluation outputs, milestone summaries, comparison artifacts.

For quick handoff navigation, start with:

- `docs/index.md`
- `docs/repo_navigation.md`
- `docs/project_status_snapshot.md`
- `docs/dependencies_and_runtime.md`

## How to run key flows locally

> Python 3.11+ recommended.

### 1) Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Run retrieval regression and milestone eval

```bash
# Day 61 baseline regression pack
python retrieval/eval/run_day61_regression_pack.py

# Day 63 dense baseline (chargram_hash_v1)
python retrieval/indexing/build_day63_dense_index.py
python retrieval/eval/run_day63_dense_regression.py --rebuild-index

# Day 63B dense upgrade path (bge-m3, optional runtime)
python crawler/prep/build_day63b_dense_ready_chunks.py
python retrieval/indexing/build_day63b_bge_m3_dense_index.py
python retrieval/eval/run_day63b_dense_regression.py --rebuild-index
python retrieval/eval/build_day63b_dense_vs_baselines_comparison.py
```

### 3) Run API locally

```bash
uvicorn app.main:app --reload
```

Open:

- API root/demo: `http://127.0.0.1:8000/`
- research endpoint: `POST /api/research/query`

## Current status and pause point

The project is currently paused at **Day 63B runtime validation**:

- code/spec/eval scaffolding exists
- output artifacts include runtime-error evidence when `FlagEmbedding` backend is unavailable
- Day 63B should remain labeled in-progress until bge-m3 runtime is verified end-to-end in local execution

## Recommended next step

Resolve Day 63B runtime dependency path (FlagEmbedding + model runtime), rerun Day 63B regression/comparison, then start Day 64 score-fusion experiments with BM25 exact-match guardrails.
