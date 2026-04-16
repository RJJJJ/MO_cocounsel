# Deterministic Metadata Extraction Baseline Spec (Day 39)

## Why this is the next priority

Day 38 already stabilized the **metadata-generation target schema** contract (`core_case_metadata` + `generated_digest_metadata`).
With a stable output shape, the highest-value next step is to provide a **reproducible deterministic baseline** for digest field filling so the team can:

1. measure population behavior now,
2. detect failure modes before any LLM path,
3. build a clean benchmark for future model-based improvements.

This round intentionally prioritizes consistency and traceability over language quality.

## Scope constraints

- Local-only execution.
- No database integration.
- No external APIs.
- No LLM generation.
- Input source: prepared corpus chunk records.

## Target fields in this baseline

Under `generated_digest_metadata`, this baseline deterministically extracts:

- `case_summary`
- `holding`
- `legal_basis`
- `disputed_issues`

## Field-by-field extraction rules

## 1) `case_summary`

### zh
- Try heading-block extraction after `摘要` / `案情摘要`.
- Stop when encountering later structural headings (e.g., `裁判`, `決定`, `理由說明`, `事實`, `法律依據`).
- Clip to fixed max length.

### pt
- Try heading-block extraction after `SUMÁRIO` / `RESUMO`.
- Stop at structural headings (e.g., `DECISÃO`, `FUNDAMENTAÇÃO`, `ACORDAM`, `RELATÓRIO`).
- Clip to fixed max length.

### fallback
- Use first two deterministic sentence splits from combined case text.
- If text is empty, return empty string.

## 2) `holding`

### zh
- Sentence-level keyword scan for dispositive cues (`裁定`, `判決`, `決定`, `駁回`, `改判`, `判處`, `維持原判`, `上訴理由不成立`).
- Prefer the last matched sentence as operative outcome proxy.

### pt
- Sentence-level keyword scan (`acordam`, `decisão`, `decidem`, `julgar`, `negar provimento`, `conceder provimento`, `improcedente`, `procedente`, `condenar`, `absolver`).
- Prefer last matched sentence.

### fallback
- Use final sentence of text.
- If text is empty, return empty string.

## 3) `legal_basis`

### zh
- Regex extraction of article references like `第123條`, `第211條` (including `之` variants).
- Deduplicate in stable order and cap list length.

### pt
- Regex extraction of article references like `art. 123`, `artigo 123.º`.
- Deduplicate in stable order and cap list length.

### fallback
- Return empty list when no legal article mention is found.

## 4) `disputed_issues`

### zh
- Extract inline issue list from heading-like patterns such as `主要問題:` / `爭議焦點:`.
- Split by `、，,;；`.

### pt
- Extract from patterns such as `Assunto:` / `Questões:`.
- Split by `、，,;；`.

### fallback
- Use `core_case_metadata.case_type` as single-item list when no explicit issue phrase is found.
- If neither text issues nor case type exists, return empty list.

## zh vs pt handling notes

- Different header lexicons are used for summary and issue extraction.
- Different dispositive/holding keyword sets are used.
- Different legal article regex patterns are used.
- Shared normalization (whitespace cleanup, deterministic clipping, stable dedupe ordering) is language-agnostic.

## Population and reporting outputs

Baseline run outputs:

1. **Per-case shaped metadata output** (`.jsonl`) matching Day 38 target schema envelope.
2. **Field-level population stats** for the four required digest fields.
3. Text report summarizing:
   - cases processed
   - case_summary populated
   - holding populated
   - legal_basis populated
   - disputed_issues populated
   - whether baseline appears successful

## Limitations

- Heuristic-only extraction; no semantic interpretation.
- Header quality depends on source formatting consistency.
- Legal basis regex may miss non-standard article citations.
- Holding detection can capture non-dispositive sentences in long narratives.
- This is a deterministic baseline, **not** a high-quality digest generator.

## Recommended next step

Choose one immediate follow-up while preserving deterministic evaluability:

1. Add a **local dense retrieval stub** and test deterministic fusion impact on metadata-support snippets.
2. Build a **metadata field evaluation set** (small human-labeled benchmark for summary/holding/legal-basis/issues coverage and precision).
