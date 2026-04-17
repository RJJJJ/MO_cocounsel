# Dependencies and Runtime Notes

This document summarizes practical dependency/runtime requirements for MO_cocounsel as of Day 63B in-progress state.

## Core dependencies

Installed by `requirements.txt`:

- `fastapi`, `uvicorn`, `pydantic`
  - for API surface (`app/main.py`, `app/api/research.py`)
- `requests`, `beautifulsoup4`, `playwright`
  - for source probing/crawling/parsing flows in `crawler/`
- `jieba`
  - optional-in-code tokenizer enhancement used by BM25 prototype in auto/jieba mode
- `opencc-python-reimplemented`
  - Traditional Chinese normalization in metadata pipelines
- `pytest`
  - test execution (`tests/`)

## Optional / experimental dependencies

### Day 63B dense upgrade (bge-m3)

Feature path:

- `crawler/retrieval/day63b_bge_m3_dense.py`
- `retrieval/indexing/build_day63b_bge_m3_dense_index.py`
- `retrieval/eval/run_day63b_dense_regression.py`

Required runtime stack when enabling this feature:

- `FlagEmbedding`
- `torch`
- `transformers`

These are intentionally not required for baseline BM25/API operation.

## Feature-to-runtime mapping

- Core retrieval (BM25 / Day 61 / Day 62):
  - Python stdlib + `jieba` (optional behavior) only.
- API serving:
  - `fastapi` + `uvicorn`.
- Crawling/parsing:
  - `requests` + `beautifulsoup4`; `playwright` for browser-based probe/parser paths.
- Metadata normalization/generation toolchain:
  - `opencc-python-reimplemented` and local model runtime setup (outside strict pip-only scope).
- Day 63 dense baseline (`chargram_hash_v1`):
  - no heavy ML dependency required.
- Day 63B bge-m3 dense baseline:
  - requires `FlagEmbedding` stack.

## Known runtime blockers

- Current Day 63B local runtime may fail if `FlagEmbedding` backend is unavailable.
- Existing Day 63B summary artifact records this exact blocker (`runtime_error: FlagEmbedding is required ...`).
- Until runtime is validated and rerun succeeds, Day 63B should remain marked as in-progress.

## Practical install guidance

1. Install core dependencies first:

```bash
pip install -r requirements.txt
```

2. Only if running Day 63B dense flows, install optional stack:

```bash
pip install FlagEmbedding torch transformers
```

3. Re-run Day 63B eval commands after optional stack installation.
