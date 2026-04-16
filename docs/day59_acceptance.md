# Day 59 Acceptance

## Today objective
Build a stable **multi-court full-corpus assembly pipeline** that crawls each court separately, then merges and deduplicates into one authoritative corpus output for downstream retrieval/eval/product usage.

## Why Day 59 matters
The project already proved `court=all` is useful for broad coverage and demo validation, but this mode should not be treated as authoritative full-harvest. Day 59 shifts authority to a more auditable ingestion strategy:

- per-court crawl (`tui`, `tsi`, `tjb`, `ta`)
- merge into one corpus candidate pool
- dedupe after merge with reason breakdown
- preserve provenance/traceability for every kept record
- attach metadata after authoritative merge (model-preferred, deterministic fallback)

## Deliverables
1. `crawler/pipeline/build_full_corpus_from_all_courts.py`
   - Orchestrates per-court crawling (or explicit manifest overrides).
   - Builds merged authoritative corpus from per-court outputs.
   - Deduplicates post-merge with auditable duplicate-reason stats.
   - Preserves provenance for traceability.
   - Emits merged manifest + JSON/TXT reports.
2. Metadata attachment stage clarification and implementation notes in code/docs:
   - post-merge attachment timing
   - model-generated preferred source
   - deterministic baseline fallback/benchmark/regression guard retained
   - default local model policy unchanged (`qwen2.5:3b-instruct`)
3. Scoped documentation updates (no README change):
   - Day 59 flow and rationale
   - limitations after Day 59
   - Day 60 recommendation: full-corpus retrieval eval/regression pack

## Explicit authoritative flow (Day 59)

```text
per-court crawl
-> merge/dedupe authoritative corpus
-> downstream prep/retrieval consumption
-> attach preferred metadata source where available
-> deterministic fallback where needed
```

## Explicit note on `court=all`
`court=all` remains valuable for broad coverage checks, debugging, and demo workflows, but **is not the authoritative final full-harvest source** after Day 59.

## Acceptance checklist
- [ ] New Day 59 script exists at `crawler/pipeline/build_full_corpus_from_all_courts.py`.
- [ ] Script supports per-court orchestration for `tui`, `tsi`, `tjb`, `ta`.
- [ ] Script does not rely on `court=all` as authoritative merged source.
- [ ] Script supports explicit input/output path override.
- [ ] Script emits merged manifest + local report/stats artifacts.
- [ ] Script logs per-court counts and merged total count.
- [ ] Script logs duplicate totals and duplicate-reason breakdown.
- [ ] Provenance fields are preserved for traceability in merged output.
- [ ] Metadata attachment policy is explicitly documented as post-merge.
- [ ] Model-generated metadata remains preferred when available.
- [ ] Deterministic baseline remains fallback and regression guard.
- [ ] Default model policy remains unchanged.
- [ ] No large generated artifact committed.
- [ ] README unchanged.
- [ ] No frontend contract changes.
- [ ] No LangChain/LlamaIndex/agent workflow introduced.

## Evidence developer must provide
- Changed file list (code + docs only).
- Example CLI commands (crawl mode and explicit-manifest mode).
- Sample expected merged report/manifest shape.
- Command output showing at least one relevant check execution.
- Concise explanation of how Day 59 changes authoritative pipeline behavior.
