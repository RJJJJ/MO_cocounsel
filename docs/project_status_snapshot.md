# Project Status Snapshot (Day 63B In-Progress)

## Current stage

- Program phase: retrieval-first architecture hardening.
- Immediate focus: Day 63B dense upgrade runtime validation before Day 64 fusion.

## Completed milestones by day

- Day 60: per-court convergence crawl + merge/dedupe authoritative corpus baseline.
- Day 61: retrieval regression pack accepted (10/10 pass).
- Day 62: BM25+ strengthening accepted (still 10/10 pass).
- Day 63: dense retrieval baseline established (`chargram_hash_v1`) with dense-only pass rate 50% (baseline milestone complete, not production default path).

## Latest accepted state

- Latest clearly accepted and stable retrieval state is Day 62 BM25+ on top of Day 61 regression pack behavior.
- Day 63 is accepted as a baseline-building milestone, not as a replacement for BM25 default path.

## In-progress state

- Day 63B bge-m3 dense upgrade:
  - build/eval/spec/acceptance scaffolding exists.
  - dense-ready chunk path from authoritative full corpus exists.
  - runtime may fail when `FlagEmbedding` is unavailable.

## Current blocker and next action

- Blocker: Day 63B runtime dependency path (`FlagEmbedding` stack) not guaranteed in current environment.
- Next action: install/verify Day 63B runtime stack, rerun full Day 63B commands, regenerate comparison output, and update acceptance evidence.

## What is stable

- Authoritative flow contract:
  - per-court convergence crawl → merge/dedupe authoritative corpus → retrieval consumption → post-merge metadata attach.
- Source-of-truth principle:
  - authoritative full-case merged corpus is upstream authority.
- Retrieval default behavior:
  - BM25+ path remains stable and regression-tested.
- Metadata policy:
  - model-generated preferred, deterministic fallback retained.
  - default model remains `qwen2.5:3b-instruct`.

## What is experimental

- Day 63B bge-m3 dense path and its runtime portability.
- Any future Day 64 score-fusion formulation until acceptance criteria are met.

## What should not be changed casually

- `sentence_id` authoritative identity contract.
- Authoritative flow sequence and post-merge metadata policy.
- Day 61/62 regression baseline expectations.
- API contract and retrieval default path semantics while Day 63B is unresolved.

## Forward roadmap snapshot

- Day 61: completed.
- Day 62: completed.
- Day 63: completed (baseline).
- Day 63B: in progress (runtime-dependent).
- Day 64: planned next milestone (score fusion).
