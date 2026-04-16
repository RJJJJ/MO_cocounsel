# Day 45 Acceptance

## Today objective

Expand the local model metadata generation sample batch and add Traditional Chinese normalization as a post-generation step for model-generated metadata fields.

## Deliverables

- `crawler/metadata/connect_local_chinese_model_metadata_generation.py`
  - expands default sample-batch coverage beyond Day 44
  - keeps local-only metadata generation path (no cloud API / no DB)
  - adds post-generation Traditional Chinese normalization before write
  - adds normalization audit/control outputs (`script_normalization_applied`, `output_script`)
  - updates report/terminal summary with normalization and expanded-batch success indicators

- `crawler/metadata/traditional_chinese_normalization.py`
  - provides local normalization helper for generated Chinese metadata text
  - prefers local converter support and includes local fallback conversion path

- `crawler/metadata/traditional_chinese_normalization_in_metadata_spec.md`
  - documents rationale, normalized fields, protected structured fields, flow placement, limitations, and recommended next steps

- local report output path (runtime/local acceptance output):
  - `data/eval/local_model_metadata_generation_report.txt`

## Acceptance checklist

- [ ] No vector retrieval work added.
- [ ] No database work added.
- [ ] No cloud model integration added.
- [ ] Local-only model backend preserved.
- [ ] Sample batch expanded (still sample-only; not full 77-case run).
- [ ] Traditional Chinese normalization runs before output write.
- [ ] Normalization covers:
  - [ ] `case_summary`
  - [ ] `holding`
  - [ ] `disputed_issues`
  - [ ] Chinese description text in `legal_basis` entries
- [ ] Structured fields remain unmutated (case number / URLs / source chunk IDs / core structured metadata).
- [ ] Output includes audit/control fields:
  - [ ] `script_normalization_applied`
  - [ ] `output_script`
- [ ] Report includes:
  - [ ] sample cases selected
  - [ ] model-generated cases written
  - [ ] generation success count
  - [ ] script normalization applied yes/no
  - [ ] whether expanded local model metadata generation batch appears successful
- [ ] Terminal output includes required summary lines above.
- [ ] README unchanged.
- [ ] No large generated artifacts committed.

## Evidence developer must provide

1. Command used to run Day 45 expanded local sample batch generation.
2. Terminal output snippet containing all required summary lines.
3. Path to local report output:
   - `data/eval/local_model_metadata_generation_report.txt`
4. Confirmation that the committed diff contains code/docs only and excludes large generated artifacts.
