# Day 47 Acceptance

## Today objective
Keep the current default local metadata model unchanged and refine the metadata prompt/control loop to improve structured extraction quality before any future model promotion.

## Deliverables
- `crawler/metadata/build_metadata_model_prompt_eval_loop.py`
- `crawler/metadata/connect_local_chinese_model_metadata_generation.py`
- `crawler/metadata/metadata_prompt_templates.py`
- `crawler/metadata/metadata_model_prompt_eval_loop_spec.md`
- `docs/day47_acceptance.md`
- Local acceptance outputs (not committing large generated artifacts):
  - `data/eval/metadata_model_prompt_eval_loop_report.txt`
  - `data/eval/metadata_prompt_refinement_notes.txt` (optional notes)

## Acceptance checklist
- [ ] Current default local model remains unchanged (no promotion).
- [ ] Prompt loop adds at least one new prompt version (e.g. `day47_prompt_a`).
- [ ] Prompt/control instructions are strengthened for schema-constrained JSON output.
- [ ] Field-level instructions are clearer for:
  - [ ] `case_summary`
  - [ ] `holding`
  - [ ] `legal_basis`
  - [ ] `disputed_issues`
- [ ] Prompt refinements target:
  - [ ] shorter/cleaner `case_summary`
  - [ ] more dispositive `holding`
  - [ ] less noisy `disputed_issues`
- [ ] Traditional Chinese normalization flow is preserved.
- [ ] Auditability is preserved with:
  - [ ] `model_name`
  - [ ] `prompt_version`
  - [ ] `generation_status`
  - [ ] `script_normalization_applied`
- [ ] Report/terminal output includes at least:
  - [ ] current default model used
  - [ ] prompt versions evaluated
  - [ ] sample cases processed
  - [ ] successful generations
  - [ ] comparison runs completed
  - [ ] whether refinement loop appears successful
- [ ] Deterministic baseline remains benchmark/fallback.
- [ ] No README modifications.
- [ ] No large generated artifacts committed.
- [ ] No vector retrieval/database/cloud model integration in this round.

## Evidence developer must provide
1. Command used to run the Day 47 prompt/eval loop locally (with parameters).
2. Terminal output snippet showing required Day 47 summary lines.
3. Local report path(s) and key summary section.
4. Git diff showing code/docs-focused changes only (no large generated outputs).
