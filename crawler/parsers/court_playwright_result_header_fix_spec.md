# Day 16B spec: paginated result-card header token parsing fix

## Remaining bug after Day 16A
Day 16A fixed card boundaries, but header parsing still used fuzzy extraction from the whole card text. In cards where table labels and data are in one line, extraction drifted:
- `decision_date` stayed correct
- `case_number` was polluted by date fragments (e.g., `03/2026`)
- `case_type` was polluted by numeric fragments (e.g., `26/`)

Example raw header pattern:
- `判決/批示日期 案件編號 類別 裁判書/批示全文 26/03/2026 36/2026 刑事訴訟程序的上訴`

## Header-token parsing strategy
For each result card:
1. Locate a **header block** before body labels such as `主題 / 摘要 / 裁判結果 / 裁判書製作法官 / 助審法官`.
2. Parse tokens in strict order inside header block:
   - `decision_date`
   - `case_number`
   - `case_type`
3. Do not infer case number/case type by fuzzy regex across full card text.

## Table-header label stripping strategy
If header line contains any table labels below, strip them **before** token parsing:
- `判決/批示日期`
- `案件編號`
- `類別`
- `裁判書/批示全文`

Then parse the cleaned header stream in ordered tokens.

## Expected token shapes
- `decision_date`: `dd/mm/yyyy`
- `case_number`: `number/year` (examples: `36/2026`, `686/2025`, `1026/2025`)
- `case_type`: remaining non-empty header text after case number

## Contamination reduction goal
Maintain Day 16A card segmentation and Day 15 link preservation unchanged, while reducing header-token pollution so that:
- valid `case_number` count increases
- valid `case_type` count increases
- suspected contamination count decreases significantly

## Recommended next step
Choose one:
1. batch text-detail extraction from header-fixed paginated cards, or
2. inspect more result-page layout variants and extend header-block detection for those variants.
