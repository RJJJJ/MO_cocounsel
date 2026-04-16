# Improved Deterministic Metadata Extraction Rules Spec (Day 41)

## Why rule refinement is now the next priority

Day 40 field-level evaluation already showed the deterministic baseline was strongest on `legal_basis` and `disputed_issues`, while `case_summary` lagged behind and `holding` was only mid-tier. Given that imbalance, Day 41 prioritizes targeted rule refinement (not infra expansion) to improve semantic quality where it is weakest while preserving stronger fields.

## Weakest field and root causes

### Weakest field: `case_summary`

Observed causes in baseline behavior:
- summary blocks occasionally bled into later sections (`裁判書製作人`, procedural sections, relator headers)
- fallback summaries were often too long and noisy
- heading boundaries were broad, causing mixed narrative + legal citation clutter
- language-specific structure (`zh` 主題/主要問題; `pt` Assunto/Descritores/SUMÁRIO) was underused

## Rule changes by field

## A) `case_summary` (primary)

- Added heading-first concise extraction:
  - `zh`: prefer `主要問題` / `重要法律問題` / `主題`
  - `pt`: prefer `Assunto` / `Descritores`
- Added tighter heading block stop conditions to avoid spillover into:
  - authorship lines (`裁判書製作人`, `O Relator`)
  - court body headers (`澳門特別行政區`, `ACORDAM`)
  - procedural section starts (`一、`, `I. RELATÓRIO`, etc.)
- Added sentence cleanup for enumerators and parenthetical citation noise.
- Added shorter fallback composition (1-2 cleaned sentences only).

## B) `holding` (secondary)

- Replaced single keyword last-match strategy with a scored dispositive sentence selector.
- Added stronger zh/pt dispositive lexicons for high-value outcomes:
  - e.g., `駁回`, `不予批准`, `維持原審`, `上訴理由不成立`
  - e.g., `negar provimento`, `julgar improcedente`, `mantendo-se`, `acordam`
- Added length penalty to reduce long noisy candidate sentences.
- Kept deterministic fallback to tail sentences when no dispositive trigger exists.

## C) Secondary cleanup (non-breaking)

- `disputed_issues`: kept close to baseline (pattern-first + `case_type` fallback) to avoid quality regression.
- `legal_basis`: kept extraction stable; only minor normalization consistency for PT casing.

## Expected effect

- Higher overlap signals for `case_summary` through cleaner, heading-grounded, concise outputs.
- Better `holding` alignment via dispositive sentence scoring instead of naïve terminal selection.
- Maintain high coverage and normalized overlap for `legal_basis` / `disputed_issues`.

## Known remaining limitations

- OCR/layout noise can still distort headings in some long judgments.
- No deep document structure parser; section boundaries remain heuristic.
- Summary compression is extractive; no abstractive rewriting by design.
- Some holdings are distributed across multiple sentences and may need multi-sentence assembly.

## Recommended next step

Prefer building a **metadata generation comparison harness (baseline vs improved)** to produce side-by-side per-case diffs and per-field delta metrics before any retrieval infra expansion.

Alternative (if retrieval work must proceed): add a **local dense retrieval stub** only after metadata deltas are transparently measured.
